"""Telemetry facade API (BL-076) — single source for Dashboard + Monitoring.

Exposes four aggregate views backed by AuditLog / LLMProvider / security analytics:
- ``/telemetry/summary``    high-level summary (events, latency, tokens, cost)
- ``/telemetry/operations`` live ops panel (requests, tokens, p50/p95, blocks)
- ``/telemetry/security``   security analytics (threats, rules, breakdown)
- ``/telemetry/traces``     OTel trace summaries
"""

from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import USE_STUDIO, VIEW_AUDIT_LOGS, require_any_permission
from app.db.session import get_db
from app.models.governance import AuditLog
from app.models.tenant import User
from app.schemas.governance import TraceSummaryResponse
from app.schemas.security import SecurityOverviewResponse
from app.schemas.sla import GatewaySlaResponse
from app.schemas.telemetry import TelemetryOperationsResponse, TelemetrySummaryResponse
from app.services.telemetry_service import (
    _resolve_range,
    build_telemetry_operations,
    build_telemetry_security,
    build_telemetry_summary,
)
from app.services.trace_replay_service import build_trace_from_audit_log
from app.services.sla_service import build_gateway_sla

router = APIRouter()

_require_telemetry = require_any_permission(USE_STUDIO, VIEW_AUDIT_LOGS)


@router.get("/telemetry/summary", response_model=TelemetrySummaryResponse)
async def telemetry_summary(
    current_user: Annotated[User, Depends(_require_telemetry)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
) -> TelemetrySummaryResponse:
    payload = await build_telemetry_summary(
        db,
        current_user.tenant_id,
        from_date=from_date,
        to_date=to_date,
    )
    return TelemetrySummaryResponse(**payload)


@router.get("/telemetry/operations", response_model=TelemetryOperationsResponse)
async def telemetry_operations(
    current_user: Annotated[User, Depends(_require_telemetry)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
) -> TelemetryOperationsResponse:
    payload = await build_telemetry_operations(
        db,
        current_user.tenant_id,
        from_date=from_date,
        to_date=to_date,
    )
    return TelemetryOperationsResponse(**payload)


@router.get("/telemetry/sla", response_model=GatewaySlaResponse)
async def telemetry_sla(
    current_user: Annotated[User, Depends(_require_telemetry)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
) -> GatewaySlaResponse:
    payload = await build_gateway_sla(
        db,
        current_user.tenant_id,
        from_date=from_date,
        to_date=to_date,
    )
    return GatewaySlaResponse(**payload)


@router.get("/telemetry/security", response_model=SecurityOverviewResponse)
async def telemetry_security(
    current_user: Annotated[User, Depends(_require_telemetry)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SecurityOverviewResponse:
    return await build_telemetry_security(db, current_user.tenant_id)


@router.get("/telemetry/traces", response_model=list[TraceSummaryResponse])
async def telemetry_traces(
    current_user: Annotated[User, Depends(_require_telemetry)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[TraceSummaryResponse]:
    range_start, range_end = _resolve_range(from_date, to_date)
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.tenant_id == current_user.tenant_id,
            AuditLog.timestamp >= range_start,
            AuditLog.timestamp < range_end,
        )
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [TraceSummaryResponse(**build_trace_from_audit_log(log)) for log in logs]


@router.get("/telemetry/traces/{audit_id}", response_model=TraceSummaryResponse)
async def telemetry_trace_detail(
    audit_id: str,
    current_user: Annotated[User, Depends(_require_telemetry)],
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
