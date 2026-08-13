"""Telemetry facade aggregation (BL-076) — single source for Dashboard + Monitoring.

The pure ``summarize_*`` helpers are unit-testable without a database; the
``build_*`` helpers query AuditLog / LLMProvider and delegate to them.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.date_range import default_last_n_days, parse_date_range
from app.models.governance import AuditLog, LLMProvider
from app.services.compounding_cost_service import DEFAULT_COST_PER_1K, _model_rate, _usd
from app.services.security_analytics_service import build_security_overview


# ---------------------------------------------------------------------------
# Pure aggregation helpers (unit-testable)
# ---------------------------------------------------------------------------

def _resolve_range(from_date: str | None, to_date: str | None) -> tuple[datetime, datetime]:
    range_start, range_end = parse_date_range(from_date, to_date)
    if range_start is None and range_end is None:
        return default_last_n_days(7)
    if range_start is None:
        range_start = range_end - timedelta(days=7)
    if range_end is None:
        range_end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return range_start, range_end


def summarize_events(
    rows: list[tuple[str, str, str, datetime, dict | None]],
    *,
    avg_latency_ms: int = 0,
    p95_latency_ms: int = 0,
    period_days: int = 7,
) -> dict[str, Any]:
    """Aggregate audit rows into a high-level summary.

    Each row is ``(status, action, risk, timestamp, usage_metadata)``.
    """
    total = len(rows)
    allowed = sum(1 for row in rows if row[0] == "allowed")
    blocked = sum(1 for row in rows if row[0] == "blocked")
    review = sum(1 for row in rows if row[0] == "review")

    by_action: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    daily: dict[str, dict[str, Any]] = {}
    total_tokens = 0
    total_cost = 0.0
    models: set[str] = set()

    for status, action, risk, timestamp, meta in rows:
        by_action[action] = by_action.get(action, 0) + 1
        by_risk[risk] = by_risk.get(risk, 0) + 1
        day = timestamp.astimezone(UTC).strftime("%b %d")
        bucket = daily.setdefault(day, {"date": day, "total": 0, "blocked": 0})
        bucket["total"] += 1
        if status == "blocked":
            bucket["blocked"] += 1
        if isinstance(meta, dict):
            tokens = int(meta.get("total_tokens") or 0)
            model = str(meta.get("model") or "unknown")
            if tokens:
                total_tokens += tokens
                total_cost += _usd(tokens, _model_rate(model, DEFAULT_COST_PER_1K))
                models.add(model)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "period_days": period_days,
        "total_events": total,
        "allowed": allowed,
        "blocked": blocked,
        "under_review": review,
        "block_rate": round(blocked / total * 100, 1) if total else 0.0,
        "avg_latency_ms": avg_latency_ms,
        "p95_latency_ms": p95_latency_ms,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "active_models": len(models),
        "by_action": [
            {"action": key, "count": value}
            for key, value in sorted(by_action.items(), key=lambda item: item[1], reverse=True)
        ],
        "by_risk": [
            {"risk": key, "count": value}
            for key, value in sorted(by_risk.items(), key=lambda item: item[1], reverse=True)
        ],
        "daily_trend": sorted(daily.values(), key=lambda item: item["date"]),
    }


def summarize_operations(
    rows: list[tuple[str, str, str, str, str, datetime, dict | None]],
    *,
    p50_latency_ms: int = 0,
    p95_latency_ms: int = 0,
) -> dict[str, Any]:
    """Aggregate audit rows into the live operations panel.

    Each row is ``(status, action, risk, actor, resource, timestamp, usage_metadata)``.
    """
    total = len(rows)
    allowed = sum(1 for row in rows if row[0] == "allowed")
    blocked = sum(1 for row in rows if row[0] == "blocked")
    review = sum(1 for row in rows if row[0] == "review")

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    by_action: dict[str, int] = {}
    by_status: dict[str, int] = {}
    recent_blocked: list[dict[str, Any]] = []

    for status, action, risk, actor, resource, timestamp, meta in rows:
        by_action[action] = by_action.get(action, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        if isinstance(meta, dict):
            prompt_tokens += int(meta.get("prompt_tokens") or 0)
            completion_tokens += int(meta.get("completion_tokens") or 0)
            total_tokens += int(meta.get("total_tokens") or 0)
        if status == "blocked" and len(recent_blocked) < 20:
            recent_blocked.append(
                {
                    "id": str(uuid.uuid4()),
                    "timestamp": timestamp.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                    "actor": actor,
                    "action": action,
                    "resource": resource,
                    "risk": risk,
                    "details": "",
                }
            )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "requests_total": total,
        "requests_allowed": allowed,
        "requests_blocked": blocked,
        "requests_review": review,
        "tokens_total": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "p50_latency_ms": p50_latency_ms,
        "p95_latency_ms": p95_latency_ms,
        "block_rate": round(blocked / total * 100, 1) if total else 0.0,
        "by_action": [
            {"action": key, "count": value}
            for key, value in sorted(by_action.items(), key=lambda item: item[1], reverse=True)
        ],
        "by_status": [
            {"status": key, "count": value}
            for key, value in sorted(by_status.items(), key=lambda item: item[1], reverse=True)
        ],
        "recent_blocked": recent_blocked,
    }


def _provider_latency_stats(provider_rows: list[Any]) -> tuple[int, int]:
    """Derive avg/p95 latency from LLMProvider stats (mirrors observability)."""
    active = [row for row in provider_rows if row.is_active and (row.total_requests or 0) > 0]
    if not active:
        return 0, 0
    avg = int(sum(row.avg_latency_ms or 0 for row in active) / len(active))
    maximum = max((row.avg_latency_ms or 0) for row in active)
    p95 = maximum if maximum else int(avg * 1.35) if avg else 0
    return avg, p95


# ---------------------------------------------------------------------------
# DB-backed builders
# ---------------------------------------------------------------------------

async def build_telemetry_summary(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    range_start, range_end = _resolve_range(from_date, to_date)
    period_days = max((range_end - range_start).days, 1)
    base = AuditLog.tenant_id == tenant_id
    range_filter = (AuditLog.timestamp >= range_start, AuditLog.timestamp < range_end)

    result = await db.execute(
        select(AuditLog.status, AuditLog.action, AuditLog.risk, AuditLog.timestamp, AuditLog.usage_metadata).where(
            base, *range_filter
        )
    )
    rows = [(row[0], row[1], row[2], row[3], row[4]) for row in result.all()]

    provider_rows = (
        await db.execute(
            select(LLMProvider).where(LLMProvider.tenant_id == tenant_id, LLMProvider.is_active.is_(True))
        )
    ).scalars().all()
    avg_latency_ms, p95_latency_ms = _provider_latency_stats(list(provider_rows))

    return summarize_events(
        rows,
        avg_latency_ms=avg_latency_ms,
        p95_latency_ms=p95_latency_ms,
        period_days=period_days,
    )


async def build_telemetry_operations(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    range_start, range_end = _resolve_range(from_date, to_date)
    base = AuditLog.tenant_id == tenant_id
    range_filter = (AuditLog.timestamp >= range_start, AuditLog.timestamp < range_end)

    result = await db.execute(
        select(
            AuditLog.status,
            AuditLog.action,
            AuditLog.risk,
            AuditLog.actor,
            AuditLog.resource,
            AuditLog.timestamp,
            AuditLog.usage_metadata,
        )
        .where(base, *range_filter)
        .order_by(AuditLog.timestamp.desc())
    )
    rows = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6]) for row in result.all()]

    provider_rows = (
        await db.execute(
            select(LLMProvider).where(LLMProvider.tenant_id == tenant_id, LLMProvider.is_active.is_(True))
        )
    ).scalars().all()
    _, p95_latency_ms = _provider_latency_stats(list(provider_rows))
    p50_latency_ms = int(p95_latency_ms * 0.6) if p95_latency_ms else 0

    return summarize_operations(
        rows,
        p50_latency_ms=p50_latency_ms,
        p95_latency_ms=p95_latency_ms,
    )


async def build_telemetry_security(db: AsyncSession, tenant_id: uuid.UUID):
    """Security analytics — reuses Security Center builder (single source)."""
    return await build_security_overview(db, tenant_id)
