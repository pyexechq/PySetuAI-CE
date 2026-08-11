"""Tenant model alias resolution for UAG."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.uag import UagModelMapping

DEFAULT_MAPPINGS: dict[str, dict[str, str]] = {
    "gpt-4o": {"actual_model": "gemini-1.5-pro", "target_provider": "gemini"},
    "gpt-4o-mini": {"actual_model": "gemini-1.5-flash", "target_provider": "gemini"},
    "gpt-4": {"actual_model": "llama3.2", "target_provider": "ollama"},
}


async def resolve_model_mapping(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    requested_model: str,
) -> tuple[str, str, str | None]:
    """Return (actual_model, target_provider, mapping_id or None)."""
    normalized = requested_model.strip().lower()
    if normalized in {"", "auto"}:
        return requested_model, "openai", None

    result = await db.execute(
        select(UagModelMapping).where(
            UagModelMapping.tenant_id == tenant_id,
            UagModelMapping.enabled.is_(True),
        )
    )
    rows = result.scalars().all()
    for row in rows:
        if row.requested_model.strip().lower() == normalized:
            return row.actual_model, row.target_provider, str(row.id)

    default = DEFAULT_MAPPINGS.get(normalized)
    if default:
        return default["actual_model"], default["target_provider"], None

    return requested_model, "openai", None
