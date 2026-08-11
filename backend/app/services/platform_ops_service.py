"""Cross-tenant fleet metrics for the platform operator SLA dashboard."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.gateway import _gateway_counts
from app.config import settings
from app.models.governance import AuditLog, LLMProvider
from app.models.tenant import Tenant
from app.services.health_service import build_dependency_status
from app.services.tenant_provision_service import get_tenant_admin_email, normalize_slug, tenant_has_demo_data


async def _tenant_llm_latency(db: AsyncSession, tenant_id: uuid.UUID) -> tuple[int, int]:
    result = await db.execute(
        select(func.avg(LLMProvider.avg_latency_ms), func.max(LLMProvider.avg_latency_ms)).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
            LLMProvider.total_requests > 0,
        )
    )
    avg_latency, max_latency = result.one()
    avg_ms = int(avg_latency or 0)
    p95_ms = int(max_latency or 0) if max_latency else int(avg_ms * 1.35) if avg_ms else 0
    return avg_ms, p95_ms


async def _tenant_audit_counts(db: AsyncSession, tenant_id: uuid.UUID) -> tuple[int, int]:
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    base = (AuditLog.tenant_id == tenant_id, AuditLog.timestamp >= today)
    total_result = await db.execute(select(func.count(AuditLog.id)).where(*base))
    blocked_result = await db.execute(
        select(func.count(AuditLog.id)).where(*base, AuditLog.status == "blocked")
    )
    return total_result.scalar() or 0, blocked_result.scalar() or 0


async def build_platform_ops_overview(db: AsyncSession) -> dict:
    platform_slug = normalize_slug(settings.platform_tenant_slug)
    result = await db.execute(
        select(Tenant)
        .where(Tenant.slug != platform_slug)
        .order_by(Tenant.created_at.desc())
    )
    tenants = result.scalars().all()

    fleet_requests = 0
    fleet_blocked = 0
    fleet_audit_events = 0
    latency_samples: list[int] = []
    tenant_rows: list[dict] = []

    for tenant in tenants:
        llm_total, llm_blocked = await _gateway_counts(db, tenant.id)
        audit_total, audit_blocked = await _tenant_audit_counts(db, tenant.id)
        avg_latency, p95_latency = await _tenant_llm_latency(db, tenant.id)
        admin_email = await get_tenant_admin_email(db, tenant.id)
        demo_loaded = await tenant_has_demo_data(db, tenant.id)

        fleet_requests += llm_total
        fleet_blocked += llm_blocked
        fleet_audit_events += audit_total
        if avg_latency:
            latency_samples.append(avg_latency)

        block_rate = round((llm_blocked / llm_total * 100) if llm_total else 0.0, 1)
        tenant_rows.append(
            {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "is_active": tenant.is_active,
                "admin_email": admin_email,
                "demo_data_loaded": demo_loaded,
                "subdomain": tenant.subdomain or tenant.slug,
                "llm_requests_today": llm_total,
                "llm_blocked_today": llm_blocked,
                "block_rate_pct": block_rate,
                "audit_events_today": audit_total,
                "audit_blocked_today": audit_blocked,
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
            }
        )

    active_tenants = sum(1 for tenant in tenants if tenant.is_active)
    fleet_avg_latency = int(sum(latency_samples) / len(latency_samples)) if latency_samples else 0
    health = await build_dependency_status()

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "fleet": {
            "total_tenants": len(tenants),
            "active_tenants": active_tenants,
            "suspended_tenants": len(tenants) - active_tenants,
            "llm_requests_today": fleet_requests,
            "llm_blocked_today": fleet_blocked,
            "fleet_block_rate_pct": round((fleet_blocked / fleet_requests * 100) if fleet_requests else 0.0, 1),
            "audit_events_today": fleet_audit_events,
            "avg_latency_ms": fleet_avg_latency,
        },
        "dependencies": health["dependencies"],
        "status": health["status"],
        "tenants": tenant_rows,
    }
