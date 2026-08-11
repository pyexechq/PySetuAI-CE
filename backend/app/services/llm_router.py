import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import LLMProvider, RoutingRule
from app.services.routing_conditions import evaluate_condition


def pick_weighted_provider(providers: list[LLMProvider]) -> LLMProvider | None:
    if not providers:
        return None

    weights = [max(float(provider.percentage or 0), 0.0) for provider in providers]
    total = sum(weights)
    if total <= 0:
        return providers[0]

    target = random.uniform(0, total)
    cumulative = 0.0
    for provider, weight in zip(providers, weights, strict=False):
        cumulative += weight
        if target <= cumulative:
            return provider
    return providers[-1]


async def select_model(
    requested_model: str,
    db: AsyncSession,
    tenant_id,
    routing_context: dict | None = None,
) -> tuple[str, str | None, str]:
    context = routing_context or {}
    normalized = requested_model.strip().lower()
    providers_result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
        )
    )
    providers = providers_result.scalars().all()
    for provider in providers:
        if provider.name.lower().replace(" ", "-") == normalized.replace(" ", "-"):
            return provider.name, None, "explicit"
        if normalized in provider.name.lower().replace(" ", ""):
            return provider.name, None, "explicit"

    if requested_model and requested_model != "auto":
        return requested_model, None, "passthrough"

    rules_result = await db.execute(
        select(RoutingRule)
        .where(RoutingRule.tenant_id == tenant_id, RoutingRule.status == "active")
        .order_by(RoutingRule.priority.asc())
    )
    rules = rules_result.scalars().all()
    for rule in rules:
        if evaluate_condition(rule.condition, context):
            return rule.target_model, rule.name, "rule"

    weighted = pick_weighted_provider(providers)
    if weighted is not None:
        return weighted.name, None, "weighted_pool"

    return requested_model or "gpt-4o", None, "fallback"
