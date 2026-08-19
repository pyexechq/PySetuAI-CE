"""Resolve tenant AI Assist credentials for platform-wide PySetu AI features."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.openai import ChatMessage
from app.services.gemini_client import GeminiError, call_gemini, normalize_gemini_model
from app.services.gateway_service import resolve_chat_completions_url
from app.services.integration_service import get_or_create_integration, mask_secret, resolve_ollama_base_url
from app.services.ollama_client import OllamaError, list_ollama_models, resolve_ollama_model
from app.services.secrets_service import AI_ASSIST_SECRET, GEMINI_SECRET, OPENAI_SECRET, get_tenant_secret, set_tenant_secret

AI_ASSIST_FEATURES = (
    "Policy Studio AI Helper",
    "Compliance Center AI assist",
    "Dashboard metric insights",
    "Context-aware help chat",
)

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_VLLM_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
GROQ_API_BASE = "https://api.groq.com/openai/v1"

CLOUD_PROVIDERS = frozenset({"openai", "gemini", "groq"})
LOCAL_PROVIDERS = frozenset({"ollama", "vllm", "custom"})
ALL_PROVIDERS = CLOUD_PROVIDERS | LOCAL_PROVIDERS

AI_ASSIST_PROVIDER_LABELS: dict[str, str] = {
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "groq": "Groq",
    "ollama": "Ollama (air-gap)",
    "vllm": "vLLM (air-gap)",
    "custom": "Custom OpenAI-compatible (air-gap)",
}


def supported_ai_assist_providers() -> list[str]:
    if settings.air_gap_mode:
        return sorted(LOCAL_PROVIDERS)
    return sorted(ALL_PROVIDERS)


def default_model_for_provider(provider: str) -> str:
    if provider == "gemini":
        return DEFAULT_GEMINI_MODEL
    if provider == "groq":
        return DEFAULT_GROQ_MODEL
    if provider == "ollama":
        return DEFAULT_OLLAMA_MODEL
    if provider == "vllm":
        return DEFAULT_VLLM_MODEL
    if provider == "custom":
        return DEFAULT_OPENAI_MODEL
    return DEFAULT_OPENAI_MODEL


@dataclass
class AiAssistConfig:
    enabled: bool
    provider: str
    model: str
    api_key: str | None
    base_url: str | None
    source: str

    @property
    def is_local_provider(self) -> bool:
        return self.provider in LOCAL_PROVIDERS

    @property
    def available(self) -> bool:
        if not self.enabled:
            return False
        if self.is_local_provider:
            return bool(self.base_url)
        if settings.air_gap_mode:
            return False
        return bool(self.api_key)


async def _get_integration_row(db: AsyncSession, tenant_id):
    from sqlalchemy import select

    from app.models.governance import TenantIntegration

    result = await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id))
    return result.scalar_one_or_none()


def _normalize_provider(raw: str | None) -> str:
    provider = (raw or "openai").strip().lower()
    if provider not in ALL_PROVIDERS:
        return "openai"
    if settings.air_gap_mode and provider in CLOUD_PROVIDERS:
        return "ollama"
    return provider


def _resolve_local_base_url(provider: str, row) -> str | None:
    if provider == "ollama":
        configured = (row.ai_assist_base_url or "").strip() or (row.ollama_base_url or "").strip()
        if configured:
            return resolve_ollama_base_url(configured)
        return resolve_ollama_base_url(settings.ollama_base_url)
    if provider in {"vllm", "custom"}:
        return (row.ai_assist_base_url or "").strip() or None
    return None


def _resolve_default_base_url(provider: str) -> str | None:
    if provider == "groq":
        return GROQ_API_BASE
    if provider == "ollama":
        return resolve_ollama_base_url(settings.ollama_base_url)
    return None


async def resolve_ai_assist_config(db: AsyncSession, tenant_id) -> AiAssistConfig:
    row = await _get_integration_row(db, tenant_id)
    api_key = await get_tenant_secret(db, tenant_id, AI_ASSIST_SECRET)
    source = "none"

    if api_key:
        source = "tenant_settings"
    elif row and row.ai_assist_api_key:
        api_key = row.ai_assist_api_key
        source = "tenant_settings"

    provider = _normalize_provider(row.ai_assist_provider if row else "openai")

    model = ((row.ai_assist_model if row else "") or "").strip()
    if not model:
        model = default_model_for_provider(provider)
    elif provider == "ollama" and row and row.ollama_default_model and model.startswith("gpt"):
        model = row.ollama_default_model

    base_url = _resolve_local_base_url(provider, row) if row else _resolve_default_base_url(provider)
    if provider == "groq" and not base_url:
        base_url = GROQ_API_BASE

    if not api_key and provider in CLOUD_PROVIDERS:
        if provider == "gemini":
            gateway_key = await get_tenant_secret(db, tenant_id, GEMINI_SECRET)
            if gateway_key:
                api_key = gateway_key
                source = "gateway_fallback"
                if row and row.gemini_default_model:
                    model = row.gemini_default_model.strip() or model
            else:
                gateway_openai = await get_tenant_secret(db, tenant_id, OPENAI_SECRET)
                if gateway_openai:
                    api_key = gateway_openai
                    provider = "openai"
                    source = "gateway_fallback"
        elif provider == "openai":
            gateway_key = await get_tenant_secret(db, tenant_id, OPENAI_SECRET)
            if gateway_key:
                api_key = gateway_key
                source = "gateway_fallback"
            else:
                gateway_gemini = await get_tenant_secret(db, tenant_id, GEMINI_SECRET)
                if gateway_gemini:
                    api_key = gateway_gemini
                    provider = "gemini"
                    source = "gateway_fallback"
                    if row and row.gemini_default_model:
                        model = row.gemini_default_model.strip() or DEFAULT_GEMINI_MODEL

    if provider in LOCAL_PROVIDERS and row and not (row.ai_assist_base_url or "").strip():
        if provider == "ollama" and (row.ollama_enabled or settings.air_gap_mode):
            source = "gateway_fallback" if source == "none" else source
            if row.ollama_default_model and model == DEFAULT_OLLAMA_MODEL:
                model = row.ollama_default_model

    return AiAssistConfig(
        enabled=bool(row.ai_assist_enabled) if row else False,
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        source=source,
    )


async def ai_assist_status(db: AsyncSession, tenant_id) -> dict:
    row = await _get_integration_row(db, tenant_id)
    dedicated_key = await get_tenant_secret(db, tenant_id, AI_ASSIST_SECRET)
    if dedicated_key is None and row and row.ai_assist_api_key:
        dedicated_key = row.ai_assist_api_key

    config = await resolve_ai_assist_config(db, tenant_id)
    supported = supported_ai_assist_providers()
    return {
        "enabled": bool(row.ai_assist_enabled) if row else False,
        "provider": config.provider,
        "model": config.model,
        "api_key_set": bool(dedicated_key),
        "api_key_masked": mask_secret(dedicated_key),
        "base_url": config.base_url,
        "available": config.available,
        "uses_gateway_fallback": config.source == "gateway_fallback",
        "credential_source": config.source,
        "supported_providers": supported,
        "provider_labels": {key: AI_ASSIST_PROVIDER_LABELS[key] for key in supported},
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
    base_url: str | None = None,
) -> dict:
    row = await get_or_create_integration(db, tenant_id)

    if enabled is not None:
        row.ai_assist_enabled = enabled
    if provider is not None:
        normalized = _normalize_provider(provider)
        if normalized not in supported_ai_assist_providers():
            raise ValueError(f"provider must be one of: {', '.join(supported_ai_assist_providers())}")
        row.ai_assist_provider = normalized
    if model is not None:
        row.ai_assist_model = model.strip() or row.ai_assist_model
    if base_url is not None:
        row.ai_assist_base_url = base_url.strip() or None
    if api_key is not None:
        await set_tenant_secret(db, tenant_id, AI_ASSIST_SECRET, api_key.strip() or None)

    await db.commit()
    await db.refresh(row)
    return await ai_assist_status(db, tenant_id)


async def call_openai_compatible_chat(
    model: str,
    messages: list[ChatMessage],
    api_key: str | None,
    *,
    api_base: str | None = None,
    temperature: float = 0.3,
) -> str:
    payload = {
        "model": model,
        "messages": [message.model_dump() for message in messages],
        "temperature": temperature,
    }
    url = resolve_chat_completions_url(api_base or "https://api.openai.com/v1")
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=payload)
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
        if config.provider in LOCAL_PROVIDERS and config.base_url:
            resolved_model = config.model
            if config.provider == "ollama":
                try:
                    available = await list_ollama_models(config.base_url)
                    resolved_model = resolve_ollama_model(config.model, available, config.model)
                except OllamaError:
                    resolved_model = config.model
            text = await call_openai_compatible_chat(
                resolved_model,
                messages,
                config.api_key,
                api_base=config.base_url,
                temperature=temperature,
            )
            return text, True
        if config.provider == "groq":
            text = await call_openai_compatible_chat(
                config.model,
                messages,
                config.api_key,
                api_base=config.base_url or GROQ_API_BASE,
                temperature=temperature,
            )
            return text, True
        text = await call_openai_compatible_chat(
            config.model,
            messages,
            config.api_key,
            temperature=temperature,
        )
        return text, True
    except (GeminiError, OllamaError, httpx.HTTPError, KeyError, IndexError, ValueError):
        return None, False
