"""Provider translation policy evaluation (deprecated — use routing rules)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.uag.canonical import CanonicalPrompt


@dataclass
class TranslationPolicyDecision:
    target_provider: str
    emulate_protocol: str
    policy_name: str | None = None


async def evaluate_translation_policies(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    canonical: CanonicalPrompt,
    default_provider: str,
) -> TranslationPolicyDecision:
    """Legacy UAG translation policies are retired; routing rules own provider overrides."""
    _ = (db, tenant_id, canonical)
    return TranslationPolicyDecision(target_provider=default_provider, emulate_protocol="openai")
