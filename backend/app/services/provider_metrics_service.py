"""Update LLM provider metrics from live gateway traffic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import LLMProvider


async def record_provider_request(
    db: AsyncSession,
    tenant_id,
    routed_model: str,
    latency_ms: int,
    *,
    success: bool,
) -> None:
    name = routed_model.strip()
    if not name:
        return

    result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
            LLMProvider.name.ilike(name),
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        return

    previous_count = provider.total_requests
    provider.total_requests = previous_count + 1

    if latency_ms > 0:
        if previous_count == 0:
            provider.avg_latency_ms = latency_ms
        else:
            provider.avg_latency_ms = int(
                (provider.avg_latency_ms * previous_count + latency_ms) / (previous_count + 1)
            )

    previous_successes = (provider.success_rate / 100.0) * previous_count
    new_successes = previous_successes + (1.0 if success else 0.0)
    provider.success_rate = round(new_successes / provider.total_requests * 100, 1)


async def rebalance_provider_percentages(db: AsyncSession, tenant_id) -> tuple[int, list[dict]]:
    result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
        )
    )
    providers = result.scalars().all()
    if not providers:
        return 0, []

    total_requests = sum(provider.total_requests for provider in providers)
    if total_requests <= 0:
        return 0, []

    updates: list[dict] = []
    allocated = 0.0
    for index, provider in enumerate(providers):
        previous = provider.percentage
        if index == len(providers) - 1:
            share = round(max(0.0, 100.0 - allocated), 1)
        else:
            share = round(provider.total_requests / total_requests * 100, 1)
            allocated += share
        provider.percentage = share
        updates.append(
            {
                "id": str(provider.id),
                "model": provider.name,
                "requests": provider.total_requests,
                "previous_percentage": previous,
                "percentage": share,
            }
        )

    return total_requests, updates


async def rebalance_all_tenants(db: AsyncSession) -> dict:
    from app.models.tenant import Tenant

    result = await db.execute(select(Tenant.id))
    tenant_ids = list(result.scalars().all())

    tenants_updated = 0
    providers_updated = 0
    for tenant_id in tenant_ids:
        total_requests, updates = await rebalance_provider_percentages(db, tenant_id)
        if updates:
            tenants_updated += 1
            providers_updated += len(updates)

    if tenants_updated:
        await db.commit()

    return {
        "tenants_checked": len(tenant_ids),
        "tenants_updated": tenants_updated,
        "providers_updated": providers_updated,
    }
