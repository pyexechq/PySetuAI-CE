"""Tenant model alias resolution for UAG."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import LLMProvider
from app.models.uag import UagModelMapping

DEFAULT_MAPPINGS: dict[str, dict[str, str]] = {
    "gpt-4o": {"actual_model": "gemini-1.5-pro", "target_provider": "gemini"},
    "gpt-4o-mini": {"actual_model": "gemini-1.5-flash", "target_provider": "gemini"},
    "gpt-4": {"actual_model": "llama3.2", "target_provider": "ollama"},
}


def normalize_target_provider(provider_type: str) -> str:
    normalized = provider_type.strip().lower()
    if normalized in {"custom", "openai-compatible", "openai_compatible"}:
        return "openai"
    if normalized == "google":
        return "gemini"
    return normalized


async def _resolve_provider_from_registry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    requested_model: str,
) -> tuple[str, str] | None:
    normalized = requested_model.strip().lower()
    result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
        )
    )
    providers = result.scalars().all()
    for provider in providers:
        for alias in provider.model_aliases or []:
            alias_norm = str(alias).strip().lower()
            if alias_norm == normalized or alias_norm.replace(" ", "-") == normalized.replace(" ", "-"):
                return provider.name, normalize_target_provider(provider.provider_type)
        if provider.name.strip().lower() == normalized:
            return provider.name, normalize_target_provider(provider.provider_type)

    return None


async def resolve_model_mapping(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    requested_model: str,
) -> tuple[str, str, str | None, str]:
    """Return (actual_model, target_provider, mapping_id or None, emulate_protocol)."""
    normalized = requested_model.strip().lower()
    if normalized in {"", "auto"}:
        return requested_model, "openai", None, "openai"

    result = await db.execute(
        select(UagModelMapping).where(
            UagModelMapping.tenant_id == tenant_id,
            UagModelMapping.enabled.is_(True),
        )
    )
    rows = result.scalars().all()
    for row in rows:
        if row.requested_model.strip().lower() == normalized:
            return (
                row.actual_model,
                row.target_provider,
                str(row.id),
                row.emulate_protocol or "openai",
            )

    default = DEFAULT_MAPPINGS.get(normalized)
    if default:
        return default["actual_model"], default["target_provider"], None, "openai"

    registry_match = await _resolve_provider_from_registry(db, tenant_id, requested_model)
    if registry_match:
        actual_model, target_provider = registry_match
        return actual_model, target_provider, None, "openai"

    return requested_model, "openai", None, "openai"
