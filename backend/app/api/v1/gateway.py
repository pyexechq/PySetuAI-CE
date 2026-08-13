from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.gateway_deps import get_gateway_context
from app.core.rate_limit import check_ai_rate_limits, check_ai_token_limits
from app.core.telemetry import current_trace_id
from app.db.session import get_db
from app.models.governance import AuditLog, LLMProvider, MCPServer, RoutingGroup
from app.models.tenant import Tenant, User
from app.services.alert_webhook_service import build_gateway_alert_event, dispatch_tenant_alerts
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


def _is_debug_mode(mode: str | None) -> bool:
    return (mode or "").strip().lower() == "debug"


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
    http_request: Request | None = None,
):
    user_agent = http_request.headers.get("user-agent") if http_request else None
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == ctx.tenant_id))
    tenant = tenant_result.scalar_one()

    if ctx.client_api_key_id:
        allowed, retry_after = check_ai_rate_limits(
            f"{ctx.tenant_id}:key:{ctx.client_api_key_id}",
            rpm=ctx.ai_rate_limit_rpm,
            rph=ctx.ai_rate_limit_rph,
            rpd=ctx.ai_rate_limit_rpd,
        )
        if not allowed:
            event = build_gateway_alert_event(
                action="gateway.rate_limit.block",
                actor=ctx.actor,
                resource=request.model,
                status="blocked",
                risk="medium",
                details="Gateway request blocked by API Key rate limit (RPM/RPH/RPD)",
                trace_id=current_trace_id(),
            )
            try:
                await dispatch_tenant_alerts(db, ctx.tenant_id, event)
            except Exception:
                pass
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=OpenAIErrorResponse(
                    error=OpenAIError(
                        message="API Key Rate limit exceeded.",
                        type="rate_limit_exceeded",
                        code="rate_limit_exceeded"
                    )
                ).model_dump(),
                headers={"Retry-After": str(retry_after)},
            )

    allowed, retry_after = check_ai_rate_limits(
        str(ctx.tenant_id),
        rpm=tenant.ai_rate_limit_rpm,
        rph=tenant.ai_rate_limit_rph,
        rpd=tenant.ai_rate_limit_rpd,
    )
    if not allowed:
        event = build_gateway_alert_event(
            action="gateway.rate_limit.block",
            actor=ctx.actor,
            resource=request.model,
            status="blocked",
            risk="medium",
            details="Gateway request blocked by Tenant AI rate limit (RPM/RPH/RPD)",
            trace_id=current_trace_id(),
        )
        try:
            await dispatch_tenant_alerts(db, ctx.tenant_id, event)
        except Exception:
            pass

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=OpenAIErrorResponse(
                error=OpenAIError(
                    message="Tenant Rate limit exceeded.",
                    type="rate_limit_exceeded",
                    code="rate_limit_exceeded"
                )
            ).model_dump(),
            headers={"Retry-After": str(retry_after)},
        )

    prompt_tokens = sum(len(m.content.split()) for m in request.messages if m.content)
    estimated_total = prompt_tokens + (request.max_tokens or 500)

    if ctx.client_api_key_id:
        allowed, retry_after = check_ai_token_limits(
            f"{ctx.tenant_id}:key:{ctx.client_api_key_id}",
            tpm=ctx.ai_token_limit_tpm,
            tph=ctx.ai_token_limit_tph,
            tpd=ctx.ai_token_limit_tpd,
            requested_tokens=estimated_total,
        )
        if not allowed:
            event = build_gateway_alert_event(
                action="gateway.token_budget.block",
                actor=ctx.actor,
                resource=request.model,
                status="blocked",
                risk="high",
                details=f"Gateway request blocked by API Key token budget limit (TPM/TPH/TPD). Estimated: {estimated_total} tokens",
                trace_id=current_trace_id(),
            )
            try:
                await dispatch_tenant_alerts(db, ctx.tenant_id, event)
            except Exception:
                pass
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=OpenAIErrorResponse(
                    error=OpenAIError(
                        message="API Key Token budget exceeded.",
                        type="insufficient_quota",
                        code="insufficient_quota"
                    )
                ).model_dump(),
                headers={"Retry-After": str(retry_after)},
            )

    allowed, retry_after = check_ai_token_limits(
        str(ctx.tenant_id),
        tpm=tenant.ai_token_limit_tpm,
        tph=tenant.ai_token_limit_tph,
        tpd=tenant.ai_token_limit_tpd,
        requested_tokens=estimated_total,
    )
    if not allowed:
        event = build_gateway_alert_event(
            action="gateway.token_budget.block",
            actor=ctx.actor,
            resource=request.model,
            status="blocked",
            risk="high",
            details=f"Gateway request blocked by Tenant AI token budget limit (TPM/TPH/TPD). Estimated: {estimated_total} tokens",
            trace_id=current_trace_id(),
        )
        try:
            await dispatch_tenant_alerts(db, ctx.tenant_id, event)
        except Exception:
            pass

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=OpenAIErrorResponse(
                error=OpenAIError(
                    message="Tenant Token budget exceeded.",
                    type="insufficient_quota",
                    code="insufficient_quota"
                )
            ).model_dump(),
            headers={"Retry-After": str(retry_after)},
        )

    if request.stream:
        prepared, inspection, error_message = await prepare_chat_request(request, ctx, db, user_agent=user_agent)
        if error_message and inspection and not inspection.allowed:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=OpenAIErrorResponse(
                    error=OpenAIError(message=error_message, type="policy_violation", code="pysetu_blocked")
                ).model_dump(),
            )
        if error_message or prepared is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=error_message or "Unable to prepare request"
            )
        return StreamingResponse(
            stream_chat_completion(prepared, request, ctx, db),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-PySetu-Stream": "true"},
        )

    response, inspection, error_message = await process_chat_completion(request, ctx, db, user_agent=user_agent)

    if error_message and inspection and not inspection.allowed:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=OpenAIErrorResponse(
                error=OpenAIError(message=error_message, type="policy_violation", code="pysetu_blocked")
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

    groups_result = await db.execute(
        select(RoutingGroup).where(
            RoutingGroup.tenant_id == current_user.tenant_id,
            RoutingGroup.status == "active",
        )
    )
    groups = groups_result.scalars().all()

    model_list = [ModelInfo(id=p.name, owned_by=p.provider_type) for p in providers]
    model_list.extend([ModelInfo(id=g.name, owned_by="pysetu-routing-group") for g in groups])
    if not model_list:
        model_list = [
            ModelInfo(id="gpt-4o", owned_by="openai"),
            ModelInfo(id="gemini-1.5-pro", owned_by="google"),
            ModelInfo(id="claude-3.5-sonnet", owned_by="anthropic"),
        ]
    return ModelsListResponse(data=model_list)


@openai_router.post("/v1/chat/completions")
async def chat_completions_openai(
    request: ChatCompletionRequest,
    ctx: Annotated[GatewayContext, Depends(get_gateway_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    http_request: Request,
    mode: Annotated[str | None, Query()] = None,
):
    ctx.debug_mode = _is_debug_mode(mode)
    return await _handle_chat_completions(request, ctx, db, http_request)


@admin_router.post("/chat/completions")
async def chat_completions_api(
    request: ChatCompletionRequest,
    ctx: Annotated[GatewayContext, Depends(get_gateway_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    http_request: Request,
    mode: Annotated[str | None, Query()] = None,
):
    ctx.debug_mode = _is_debug_mode(mode)
    return await _handle_chat_completions(request, ctx, db, http_request)


async def _handle_mcp_multiplex(
    request: Request,
    ctx: GatewayContext,
    db: AsyncSession,
):
    from app.services.mcp_client_service import McpToolInvokeResult, apply_tool_invoke
    from app.services.mcp_multiplex_service import dispatch_mcp_request

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON-RPC body") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON-RPC payload must be an object")

    servers_result = await db.execute(select(MCPServer).where(MCPServer.tenant_id == ctx.tenant_id))
    all_servers = list(servers_result.scalars().all())
    from app.services.mcp_portal_service import resolve_effective_mcp_access_token
    from app.services.mcp_agent_service import detect_agent, filter_servers_for_agent, toggles_from_tenant
    from app.services.secrets_service import MCP_URL_FILTER_VENDOR_KEY, get_tenant_secret

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == ctx.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    auto_hide = bool(tenant.mcp_auto_hide_destructive) if tenant else False
    agent = detect_agent(request.headers.get("user-agent"), None)
    toggles = toggles_from_tenant(tenant.mcp_agent_toggles if tenant else None)
    servers = filter_servers_for_agent(all_servers, agent, toggles)

    async def access_token_for(server):
        user_id = ctx.user.id if ctx.user else None
        return await resolve_effective_mcp_access_token(db, server, user_id=user_id)

    vendor_key = await get_tenant_secret(db, ctx.tenant_id, MCP_URL_FILTER_VENDOR_KEY)
    response = await dispatch_mcp_request(
        payload, servers, access_token_for=access_token_for, auto_hide_destructive=auto_hide,
        url_filter_policy=tenant.mcp_url_filters if tenant else None,
        vendor_api_key=vendor_key,
    )

    if str(payload.get("method") or "") == "tools/call" and "result" in response:
        meta = (response.get("result") or {}).get("_pysetu") or {}
        server_name = meta.get("server")
        for server in servers:
            if server.name == server_name:
                apply_tool_invoke(
                    server,
                    McpToolInvokeResult(ok=True, message="multiplex", latency_ms=int(meta.get("latency_ms") or 0)),
                )
                break
        await db.commit()
    return JSONResponse(response)


@openai_router.post("/v1/mcp")
@admin_router.post("/mcp")
async def mcp_multiplex_gateway(
    request: Request,
    ctx: Annotated[GatewayContext, Depends(get_gateway_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _handle_mcp_multiplex(request, ctx, db)


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

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()

    allowed, retry_after = check_ai_rate_limits(
        str(current_user.tenant_id),
        rpm=tenant.ai_rate_limit_rpm,
        rph=tenant.ai_rate_limit_rph,
        rpd=tenant.ai_rate_limit_rpd,
    )
    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": 429,
                    "message": "Rate limit exceeded.",
                    "status": "RESOURCE_EXHAUSTED"
                }
            },
            headers={"Retry-After": str(retry_after)},
        )

    contents = body.get("contents") or []
    combined = " ".join(
        part.get("text", "") for item in contents for part in item.get("parts", []) if isinstance(part, dict)
    )
    prompt_tokens = len(combined.split())
    estimated_total = prompt_tokens + 500
    allowed, retry_after = check_ai_token_limits(
        str(current_user.tenant_id),
        tpm=tenant.ai_token_limit_tpm,
        tph=tenant.ai_token_limit_tph,
        tpd=tenant.ai_token_limit_tpd,
        requested_tokens=estimated_total,
    )
    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": 429,
                    "message": "Token budget exceeded.",
                    "status": "RESOURCE_EXHAUSTED"
                }
            },
            headers={"Retry-After": str(retry_after)},
        )
    ingress = inspect_content(combined)
    if not ingress.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request blocked by PySetu policy engine.",
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
        "pysetu": {"upstream": "gemini", "inspection_action": ingress.action},
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
