"""Sync legacy UAG model aliases into the LLM provider registry."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import LLMProvider
from app.services.uag_migration_helpers import merge_aliases


async def sync_alias_to_registry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    requested_model: str,
    actual_model: str,
    provider_type: str,
) -> None:
    alias = requested_model.strip()
    model_name = actual_model.strip()
    if not alias or not model_name:
        return

    result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.name.ilike(model_name),
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        provider = LLMProvider(
            tenant_id=tenant_id,
            name=model_name,
            provider_type=provider_type.strip().lower() or "openai",
            is_active=True,
        )
        db.add(provider)
        await db.flush()

    provider.model_aliases = merge_aliases(provider.model_aliases, alias)
    if provider_type:
        provider.provider_type = provider_type.strip().lower()
