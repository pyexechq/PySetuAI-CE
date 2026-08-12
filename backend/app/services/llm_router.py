import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import LLMProvider, RoutingGroup, RoutingRule
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


def pick_routing_group_member(members: list[dict], strategy: str = "weighted") -> str | None:
    if not members:
        return None
    if strategy == "failover":
        sorted_members = sorted(members, key=lambda m: m.get("priority", 1))
        return sorted_members[0].get("model")

    weights = [max(float(m.get("weight", 0)), 0.0) for m in members]
    total = sum(weights)
    if total <= 0:
        return members[0].get("model")

    target = random.uniform(0, total)
    cumulative = 0.0
    for m, weight in zip(members, weights, strict=False):
        cumulative += weight
        if target <= cumulative:
            return m.get("model")
    return members[-1].get("model")


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

    groups_result = await db.execute(
        select(RoutingGroup).where(
            RoutingGroup.tenant_id == tenant_id,
            RoutingGroup.status == "active",
        )
    )
    groups = groups_result.scalars().all()
    for group in groups:
        if group.name.strip().lower() == normalized or group.name.strip().lower().replace(" ", "-") == normalized.replace(" ", "-"):
            target = pick_routing_group_member(group.members or [], strategy=group.strategy)
            if target:
                return target, group.name, "routing_group"

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
