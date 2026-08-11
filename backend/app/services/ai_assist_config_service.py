"""Resolve tenant AI Assist credentials for platform-wide PySetu AI features."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.openai import ChatMessage
from app.services.gemini_client import GeminiError, call_gemini, normalize_gemini_model
from app.services.integration_service import get_or_create_integration, mask_secret
from app.services.secrets_service import AI_ASSIST_SECRET, get_tenant_secret, set_tenant_secret

AI_ASSIST_FEATURES = (
    "Policy Studio AI Helper",
    "Compliance Center AI assist",
    "Dashboard metric insights",
)

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"


@dataclass
class AiAssistConfig:
    enabled: bool
    provider: str
    model: str
    api_key: str | None
    source: str

    @property
    def available(self) -> bool:
        return self.enabled and bool(self.api_key) and not settings.air_gap_mode


async def _get_integration_row(db: AsyncSession, tenant_id):
    from sqlalchemy import select

    from app.models.governance import TenantIntegration

    result = await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id))
    return result.scalar_one_or_none()


async def resolve_ai_assist_config(db: AsyncSession, tenant_id) -> AiAssistConfig:
    row = await _get_integration_row(db, tenant_id)
    api_key = await get_tenant_secret(db, tenant_id, AI_ASSIST_SECRET)
    source = "none"

    if api_key:
        source = "tenant_settings"
    elif row and row.ai_assist_api_key:
        api_key = row.ai_assist_api_key
        source = "tenant_settings"

    provider = (row.ai_assist_provider if row else "openai") or "openai"
    provider = provider.strip().lower()
    if provider not in {"openai", "gemini"}:
        provider = "openai"

    model = ((row.ai_assist_model if row else "") or "").strip()
    if not model:
        model = DEFAULT_GEMINI_MODEL if provider == "gemini" else DEFAULT_OPENAI_MODEL

    return AiAssistConfig(
        enabled=bool(row.ai_assist_enabled) if row else False,
        provider=provider,
        model=model,
        api_key=api_key,
        source=source,
    )


async def ai_assist_status(db: AsyncSession, tenant_id) -> dict:
    row = await _get_integration_row(db, tenant_id)
    api_key = await get_tenant_secret(db, tenant_id, AI_ASSIST_SECRET)
    if api_key is None and row and row.ai_assist_api_key:
        api_key = row.ai_assist_api_key

    config = await resolve_ai_assist_config(db, tenant_id)
    return {
        "enabled": bool(row.ai_assist_enabled) if row else False,
        "provider": config.provider,
        "model": config.model,
        "api_key_set": bool(api_key),
        "api_key_masked": mask_secret(api_key),
        "available": config.available,
        "features": list(AI_ASSIST_FEATURES),
        "air_gap_mode": settings.air_gap_mode,
    }


async def update_ai_assist_settings(
    db: AsyncSession,
    tenant_id,
    *,
    enabled: bool | None = None,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    row = await get_or_create_integration(db, tenant_id)

    if enabled is not None:
        row.ai_assist_enabled = enabled
    if provider is not None:
        normalized = provider.strip().lower()
        if normalized not in {"openai", "gemini"}:
            raise ValueError("provider must be 'openai' or 'gemini'")
        row.ai_assist_provider = normalized
    if model is not None:
        row.ai_assist_model = model.strip() or row.ai_assist_model
    if api_key is not None:
        await set_tenant_secret(db, tenant_id, AI_ASSIST_SECRET, api_key.strip() or None)

    await db.commit()
    await db.refresh(row)
    return await ai_assist_status(db, tenant_id)


async def call_openai_chat(
    model: str,
    messages: list[ChatMessage],
    api_key: str,
    *,
    temperature: float = 0.3,
) -> str:
    payload = {
        "model": model,
        "messages": [message.model_dump() for message in messages],
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    choice = data["choices"][0]["message"]["content"]
    return str(choice or "")


async def complete_ai_assist(
    config: AiAssistConfig,
    messages: list[ChatMessage],
    *,
    temperature: float = 0.3,
) -> tuple[str | None, bool]:
    if not config.available:
        return None, False

    try:
        if config.provider == "gemini":
            model = normalize_gemini_model(config.model, DEFAULT_GEMINI_MODEL)
            text, _ = await call_gemini(model, messages, config.api_key or "", temperature=temperature)
            return text, True
        text = await call_openai_chat(config.model, messages, config.api_key or "", temperature=temperature)
        return text, True
    except (GeminiError, httpx.HTTPError, KeyError, IndexError, ValueError):
        return None, False
