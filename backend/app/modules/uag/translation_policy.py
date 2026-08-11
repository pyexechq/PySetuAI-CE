"""Provider translation policy evaluation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.uag import UagTranslationPolicy
from app.modules.uag.canonical import CanonicalPrompt


@dataclass
class TranslationPolicyDecision:
    target_provider: str
    emulate_protocol: str
    policy_name: str | None = None


def _match_conditions(conditions: dict, canonical: CanonicalPrompt) -> bool:
    routing = canonical.metadata.get("routing_context") or {}
    for key, expected in conditions.items():
        actual = routing.get(key)
        if actual is None and key in routing.get("tags", {}):
            actual = routing["tags"][key]
        if str(actual).lower() != str(expected).lower():
            return False
    return bool(conditions)


async def evaluate_translation_policies(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    canonical: CanonicalPrompt,
    default_provider: str,
) -> TranslationPolicyDecision:
    result = await db.execute(
        select(UagTranslationPolicy)
        .where(
            UagTranslationPolicy.tenant_id == tenant_id,
            UagTranslationPolicy.enabled.is_(True),
        )
        .order_by(UagTranslationPolicy.priority.asc())
    )
    policies = result.scalars().all()
    for policy in policies:
        if _match_conditions(policy.conditions or {}, canonical):
            actions = policy.actions or {}
            return TranslationPolicyDecision(
                target_provider=str(actions.get("route_to") or actions.get("target_provider") or default_provider),
                emulate_protocol=str(actions.get("emulate") or actions.get("emulate_protocol") or "openai"),
                policy_name=policy.name,
            )
    return TranslationPolicyDecision(target_provider=default_provider, emulate_protocol="openai")
