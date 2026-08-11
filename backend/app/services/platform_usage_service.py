"""Cross-tenant AI usage metering for platform operators (BL-053)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.governance import AuditLog
from app.models.tenant import Tenant
from app.services.tenant_provision_service import get_tenant_admin_email, normalize_slug


def _token_sum_expr():
    return func.coalesce(
        func.sum(cast(AuditLog.usage_metadata["total_tokens"].as_string(), Integer)),
        0,
    )


def _prompt_sum_expr():
    return func.coalesce(
        func.sum(cast(AuditLog.usage_metadata["prompt_tokens"].as_string(), Integer)),
        0,
    )


def _completion_sum_expr():
    return func.coalesce(
        func.sum(cast(AuditLog.usage_metadata["completion_tokens"].as_string(), Integer)),
        0,
    )


async def build_platform_usage_overview(db: AsyncSession, *, days: int = 30) -> dict:
    platform_slug = normalize_slug(settings.platform_tenant_slug)
    since = datetime.now(UTC) - timedelta(days=max(days, 1))

    tenant_result = await db.execute(
        select(Tenant)
        .where(Tenant.slug != platform_slug)
        .order_by(Tenant.created_at.desc())
    )
    tenants = tenant_result.scalars().all()

    fleet_requests = 0
    fleet_tokens = 0
    fleet_prompt_tokens = 0
    fleet_completion_tokens = 0
    tenant_rows: list[dict] = []

    for tenant in tenants:
        stats = await db.execute(
            select(
                func.count(AuditLog.id),
                _token_sum_expr(),
                _prompt_sum_expr(),
                _completion_sum_expr(),
            ).where(
                AuditLog.tenant_id == tenant.id,
                AuditLog.action == "LLM Request",
                AuditLog.timestamp >= since,
                AuditLog.usage_metadata.is_not(None),
            )
        )
        request_count, total_tokens, prompt_tokens, completion_tokens = stats.one()
        requests = int(request_count or 0)
        tokens = int(total_tokens or 0)
        prompt = int(prompt_tokens or 0)
        completion = int(completion_tokens or 0)
        admin_email = await get_tenant_admin_email(db, tenant.id)

        fleet_requests += requests
        fleet_tokens += tokens
        fleet_prompt_tokens += prompt
        fleet_completion_tokens += completion

        tenant_rows.append(
            {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "is_active": tenant.is_active,
                "admin_email": admin_email,
                "llm_requests": requests,
                "total_tokens": tokens,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "avg_tokens_per_request": round(tokens / requests, 1) if requests else 0.0,
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "period_days": days,
        "fleet": {
            "total_tenants": len(tenants),
            "active_tenants": sum(1 for tenant in tenants if tenant.is_active),
            "llm_requests": fleet_requests,
            "total_tokens": fleet_tokens,
            "prompt_tokens": fleet_prompt_tokens,
            "completion_tokens": fleet_completion_tokens,
            "avg_tokens_per_request": round(fleet_tokens / fleet_requests, 1) if fleet_requests else 0.0,
        },
        "tenants": tenant_rows,
    }
