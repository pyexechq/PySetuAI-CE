from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.date_range import default_last_n_days, parse_date_range
from app.models.governance import AuditLog, LLMProvider
from app.services.http_client_pool import pool_stats


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def summarize_sla(
    rows: list[tuple[str, dict | None]], provider_count: int, period_days: int, pool: dict[str, Any] | None = None
) -> dict[str, Any]:
    latencies: list[int] = []
    overheads: list[int] = []
    for _, metadata in rows:
        if not isinstance(metadata, dict):
            continue
        if metadata.get("latency_ms") is not None:
            latencies.append(max(0, int(metadata["latency_ms"])))
        if metadata.get("gateway_overhead_ms") is not None:
            overheads.append(max(0, int(metadata["gateway_overhead_ms"])))

    total = len(rows)
    failed = sum(1 for status, _ in rows if status in {"error", "failed"})
    successful = max(0, total - failed)
    pool = pool or {"pooling_instrumented": False, "pool_reuse_rate_percent": None}
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "period_days": period_days,
        "requests_total": total,
        "successful_requests": successful,
        "failed_requests": failed,
        "availability_percent": round(successful / total * 100, 2) if total else 100.0,
        "error_rate_percent": round(failed / total * 100, 2) if total else 0.0,
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "p99_latency_ms": percentile(latencies, 0.99),
        "average_gateway_overhead_ms": round(sum(overheads) / len(overheads)) if overheads else 0,
        "providers_active": provider_count,
        "pooling_instrumented": pool["pooling_instrumented"],
        "pool_reuse_rate_percent": pool["pool_reuse_rate_percent"],
        "pool_note": "Shared HTTP client pool reuse is instrumented." if pool["pooling_instrumented"] else "Connection-pool reuse is not instrumented.",
    }


def _resolve_range(from_date: str | None, to_date: str | None) -> tuple[datetime, datetime]:
    start, end = parse_date_range(from_date, to_date)
    if start is None and end is None:
        return default_last_n_days(7)
    if start is None:
        start = end - timedelta(days=7)
    if end is None:
        end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return start, end


async def build_gateway_sla(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    start, end = _resolve_range(from_date, to_date)
    result = await db.execute(
        select(AuditLog.status, AuditLog.usage_metadata)
        .where(AuditLog.tenant_id == tenant_id, AuditLog.timestamp >= start, AuditLog.timestamp < end)
    )
    rows = list(result.all())
    provider_count = len(
        (
            await db.execute(
                select(LLMProvider.id).where(LLMProvider.tenant_id == tenant_id, LLMProvider.is_active.is_(True))
            )
        )
        .scalars()
        .all()
    )
    return summarize_sla(rows, provider_count, max((end - start).days, 1), pool_stats())