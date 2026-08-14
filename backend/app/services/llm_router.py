import random
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import LLMProvider, RoutingGroup, RoutingRule, RoutingRuleClientKey
from app.services.routing_conditions import evaluate_condition


@dataclass(frozen=True)
class RoutingDecision:
    model: str
    matched_rule: str | None = None
    strategy: str = "passthrough"
    target_provider: str | None = None
    response_format: str | None = None


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


def _match_provider_name(provider: LLMProvider, normalized: str) -> bool:
    if provider.name.lower().replace(" ", "-") == normalized.replace(" ", "-"):
        return True
    return normalized in provider.name.lower().replace(" ", "")


def _match_provider_alias(provider: LLMProvider, normalized: str) -> bool:
    for alias in provider.model_aliases or []:
        alias_norm = str(alias).strip().lower()
        if not alias_norm:
            continue
        if alias_norm == normalized:
            return True
        if alias_norm.replace(" ", "-") == normalized.replace(" ", "-"):
            return True
    return False


async def select_model(
    requested_model: str,
    db: AsyncSession,
    tenant_id,
    routing_context: dict | None = None,
    client_api_key_id=None,
) -> RoutingDecision:
    context = routing_context or {}
    normalized = requested_model.strip().lower()

    key_assignments: dict = {}
    assignment_rows = await db.execute(
        select(RoutingRuleClientKey.routing_rule_id, RoutingRuleClientKey.client_api_key_id)
        .join(RoutingRule, RoutingRule.id == RoutingRuleClientKey.routing_rule_id)
        .where(RoutingRule.tenant_id == tenant_id)
    )
    for rule_id, key_id in assignment_rows.all():
        key_assignments.setdefault(rule_id, set()).add(key_id)

    def rule_applies_to_caller(rule: RoutingRule) -> bool:
        assigned = key_assignments.get(rule.id)
        if not assigned:
            return True
        if client_api_key_id is None:
            return False
        return client_api_key_id in assigned

    providers_result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
        )
    )
    providers = providers_result.scalars().all()
    for provider in providers:
        if _match_provider_alias(provider, normalized):
            return RoutingDecision(model=provider.name, strategy="alias")
        if _match_provider_name(provider, normalized):
            return RoutingDecision(model=provider.name, strategy="explicit")

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
                return RoutingDecision(model=target, matched_rule=group.name, strategy="routing_group")

    if requested_model and requested_model != "auto":
        return RoutingDecision(model=requested_model, strategy="passthrough")

    rules_result = await db.execute(
        select(RoutingRule)
        .where(RoutingRule.tenant_id == tenant_id, RoutingRule.status == "active")
        .order_by(RoutingRule.priority.asc())
    )
    rules = rules_result.scalars().all()
    for rule in rules:
        if not rule_applies_to_caller(rule):
            continue
        if evaluate_condition(rule.condition, context):
            return RoutingDecision(
                model=rule.target_model,
                matched_rule=rule.name,
                strategy="rule",
                target_provider=rule.target_provider,
                response_format=rule.response_format,
            )

    weighted = pick_weighted_provider(providers)
    if weighted is not None:
        return RoutingDecision(model=weighted.name, strategy="weighted_pool")

    if not requested_model or requested_model.strip().lower() == "auto":
        return RoutingDecision(model="gpt-4o", strategy="fallback")
    return RoutingDecision(model=requested_model, strategy="fallback")
