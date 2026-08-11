from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.gateway_deps import get_gateway_context
from app.db.session import get_db
from app.models.governance import AuditLog, LLMProvider
from app.models.tenant import User
from app.schemas.openai import (
    ChatCompletionRequest,
    ChatMessage,
    ModelInfo,
    ModelsListResponse,
    OpenAIError,
    OpenAIErrorResponse,
)
from app.services.gateway_context import GatewayContext
from app.services.gateway_service import (
    prepare_chat_request,
    process_chat_completion,
    stream_chat_completion,
)
from app.services.gemini_client import GeminiError, call_gemini, normalize_gemini_model
from app.services.integration_service import resolve_gateway_config
from app.services.ollama_client import check_ollama_health
from app.services.policy_engine import inspect_content

openai_router = APIRouter(tags=["OpenAI Compatible Gateway"])
admin_router = APIRouter(tags=["Gateway Admin"])
router = openai_router


async def _gateway_counts(db: AsyncSession, tenant_id) -> tuple[int, int]:
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    base_filter = (
        AuditLog.tenant_id == tenant_id,
        AuditLog.action == "LLM Request",
        AuditLog.timestamp >= today,
    )
    total_result = await db.execute(select(func.count(AuditLog.id)).where(*base_filter))
    blocked_result = await db.execute(select(func.count(AuditLog.id)).where(*base_filter, AuditLog.status == "blocked"))
    return total_result.scalar() or 0, blocked_result.scalar() or 0


async def _handle_chat_completions(
    request: ChatCompletionRequest,
    ctx: GatewayContext,
    db: AsyncSession,
):
    if request.stream:
        prepared, inspection, error_message = await prepare_chat_request(request, ctx, db)
        if error_message and inspection and not inspection.allowed:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=OpenAIErrorResponse(
                    error=OpenAIError(message=error_message, type="policy_violation", code="helixguard_blocked")
                ).model_dump(),
            )
        if error_message or prepared is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=error_message or "Unable to prepare request"
            )
        return StreamingResponse(
            stream_chat_completion(prepared, request, ctx, db),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-HelixGuard-Stream": "true"},
        )

    response, inspection, error_message = await process_chat_completion(request, ctx, db)

    if error_message and inspection and not inspection.allowed:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=OpenAIErrorResponse(
                error=OpenAIError(message=error_message, type="policy_violation", code="helixguard_blocked")
            ).model_dump(),
        )

    if error_message:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error_message)

    assert response is not None
    return response


@openai_router.get("/v1/models", response_model=ModelsListResponse)
@admin_router.get("/models", response_model=ModelsListResponse)
async def list_models(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModelsListResponse:
    result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.tenant_id == current_user.tenant_id,
            LLMProvider.is_active.is_(True),
        )
    )
    providers = result.scalars().all()
    return ModelsListResponse(
        data=[ModelInfo(id=p.name, owned_by=p.provider_type) for p in providers]
        or [
            ModelInfo(id="gpt-4o", owned_by="openai"),
            ModelInfo(id="gemini-1.5-pro", owned_by="google"),
            ModelInfo(id="claude-3.5-sonnet", owned_by="anthropic"),
        ]
    )


@openai_router.post("/v1/chat/completions")
async def chat_completions_openai(
    request: ChatCompletionRequest,
    ctx: Annotated[GatewayContext, Depends(get_gateway_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _handle_chat_completions(request, ctx, db)


@admin_router.post("/chat/completions")
async def chat_completions_api(
    request: ChatCompletionRequest,
    ctx: Annotated[GatewayContext, Depends(get_gateway_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _handle_chat_completions(request, ctx, db)


@openai_router.post("/v1beta/models/{model_id}:generateContent")
async def gemini_generate_content(
    model_id: str,
    body: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    config = await resolve_gateway_config(db, current_user.tenant_id)
    if not config.gemini_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Gemini API key not configured")

    contents = body.get("contents") or []
    combined = " ".join(
        part.get("text", "") for item in contents for part in item.get("parts", []) if isinstance(part, dict)
    )
    ingress = inspect_content(combined)
    if not ingress.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request blocked by HelixGuard policy engine.",
        )

    messages = [ChatMessage(role="user", content=combined or "Hello")]
    gemini_model = normalize_gemini_model(model_id, config.gemini_default_model)
    try:
        text, resolved_model = await call_gemini(gemini_model, messages, config.gemini_api_key)
    except GeminiError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return {
        "candidates": [{"content": {"parts": [{"text": text}], "role": "model"}, "finishReason": "STOP"}],
        "modelVersion": resolved_model,
        "helixguard": {"upstream": "gemini", "inspection_action": ingress.action},
    }


@admin_router.get("/gateway/stats")
async def gateway_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    total, blocked = await _gateway_counts(db, current_user.tenant_id)
    return {"requests_today": total, "blocked_today": blocked}


@admin_router.get("/gateway/ollama/status")
async def ollama_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    config = await resolve_gateway_config(db, current_user.tenant_id)
    health = await check_ollama_health(config.ollama_base_url, config.ollama_default_model)
    health["enabled"] = config.ollama_enabled
    health["config_source"] = config.source
    return health
