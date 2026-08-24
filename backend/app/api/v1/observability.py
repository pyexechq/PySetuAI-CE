from datetime import timedelta
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.date_range import resolve_range
from app.core.rbac import USE_STUDIO, VIEW_AUDIT_LOGS, require_any_permission
from app.db.session import get_db
from app.models.governance import AuditLog, LLMProvider
from app.models.tenant import User
from app.schemas.governance import ObservabilityOverviewResponse, TraceSpanResponse, TraceSummaryResponse
from app.services.trace_replay_service import build_trace_from_audit_log

router = APIRouter()

_require_observability = require_any_permission(USE_STUDIO, VIEW_AUDIT_LOGS)


@router.get("/observability/overview", response_model=ObservabilityOverviewResponse)
async def observability_overview(
    current_user: Annotated[User, Depends(_require_observability)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
) -> ObservabilityOverviewResponse:
    tenant_id = current_user.tenant_id
    range_start, range_end = resolve_range(from_date, to_date)

    base = AuditLog.tenant_id == tenant_id
    range_filter = (AuditLog.timestamp >= range_start, AuditLog.timestamp < range_end)

    total_result = await db.execute(select(func.count(AuditLog.id)).where(base, *range_filter))
    blocked_result = await db.execute(
        select(func.count(AuditLog.id)).where(base, *range_filter, AuditLog.status == "blocked")
    )
    allowed_result = await db.execute(
        select(func.count(AuditLog.id)).where(base, *range_filter, AuditLog.status == "allowed")
    )
    review_result = await db.execute(
        select(func.count(AuditLog.id)).where(base, *range_filter, AuditLog.status == "review")
    )

    action_rows = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .where(base, *range_filter)
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
    )
    risk_rows = await db.execute(
        select(AuditLog.risk, func.count(AuditLog.id)).where(base, *range_filter).group_by(AuditLog.risk)
    )

    day_count = min(max((range_end - range_start).days, 1), 31)
    trend: list[dict] = []
    for offset in range(day_count):
        day_start = range_start + timedelta(days=offset)
        day_end = day_start + timedelta(days=1)
        if day_end > range_end:
            break
        day_total = await db.execute(
            select(func.count(AuditLog.id)).where(base, AuditLog.timestamp >= day_start, AuditLog.timestamp < day_end)
        )
        day_blocked = await db.execute(
            select(func.count(AuditLog.id)).where(
                base,
                AuditLog.timestamp >= day_start,
                AuditLog.timestamp < day_end,
                AuditLog.status == "blocked",
            )
        )
        trend.append(
            {
                "date": day_start.strftime("%b %d"),
                "total": day_total.scalar() or 0,
                "blocked": day_blocked.scalar() or 0,
            }
        )

    total = total_result.scalar() or 0
    blocked = blocked_result.scalar() or 0
    allowed = allowed_result.scalar() or 0
    review = review_result.scalar() or 0

    latency_result = await db.execute(
        select(func.avg(LLMProvider.avg_latency_ms), func.max(LLMProvider.avg_latency_ms)).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
            LLMProvider.total_requests > 0,
        )
    )
    avg_latency_raw, max_latency_raw = latency_result.one()
    avg_latency_ms = int(avg_latency_raw or 0)
    p95_latency_ms = int(max_latency_raw or 0) if max_latency_raw else int(avg_latency_ms * 1.35) if avg_latency_ms else 0

    return ObservabilityOverviewResponse(
        total_events_today=total,
        allowed_today=allowed,
        blocked_today=blocked,
        under_review_today=review,
        block_rate=round((blocked / total * 100) if total else 0.0, 1),
        avg_latency_ms=avg_latency_ms,
        p95_latency_ms=p95_latency_ms,
        error_rate=round((blocked / total * 100) if total else 0.0, 1),
        by_action=[{"action": row[0], "count": row[1]} for row in action_rows.all()],
        by_risk=[{"risk": row[0], "count": row[1]} for row in risk_rows.all()],
        daily_trend=trend,
    )


@router.get("/observability/traces", response_model=list[TraceSummaryResponse])
async def observability_traces(
    current_user: Annotated[User, Depends(_require_observability)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    dlp_only: bool = Query(False),
) -> list[TraceSummaryResponse]:
    range_start, range_end = resolve_range(from_date, to_date)
    query = select(AuditLog).where(
        AuditLog.tenant_id == current_user.tenant_id,
        AuditLog.timestamp >= range_start,
        AuditLog.timestamp < range_end,
    )
    if dlp_only:
        # Show only traces where a DLP policy was applicable (action or details match)
        query = query.where(
            or_(
                AuditLog.action == "DLP Scan",
                AuditLog.action == "PII",
                AuditLog.details.ilike("%DLP%"),
                AuditLog.details.ilike("%PII%")
            )
        )
    result = await db.execute(
        query.order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    traces = [TraceSummaryResponse(**build_trace_from_audit_log(log)) for log in logs]
    return traces


@router.get("/observability/traces/{audit_id}", response_model=TraceSummaryResponse)
async def observability_trace_detail(
    audit_id: str,
    current_user: Annotated[User, Depends(_require_observability)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TraceSummaryResponse:
    try:
        audit_uuid = uuid.UUID(audit_id.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="audit_id must be a valid UUID",
        ) from exc
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.id == audit_uuid,
            AuditLog.tenant_id == current_user.tenant_id,
        )
    )
    log = result.scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    return TraceSummaryResponse(**build_trace_from_audit_log(log))
