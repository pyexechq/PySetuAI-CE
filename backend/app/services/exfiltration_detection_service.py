"""Data exfiltration detection (Phase 5).

Pure, deterministic detectors plus async persistence helpers. Reuses the
control-plane risk conventions and the trusted-external-service set from the
MCP tool-chain service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agentic import ExfiltrationEvent
from app.services.agentic_service import risk_band
from app.services.mcp_tool_chain_service import TRUSTED_EXTERNAL_SERVICES

# Base risk per exfiltration type (0-100 scale).
EXFIL_TYPE_BASE_RISK: dict[str, int] = {
    "large_read": 40,
    "rapid_read": 50,
    "sensitive_boundary_exit": 70,
}

# Large read threshold in bytes (default 10 MB).
LARGE_READ_THRESHOLD_BYTES = 10 * 1024 * 1024
# Rapid read threshold: events within a window.
RAPID_READ_EVENT_THRESHOLD = 20
RAPID_READ_WINDOW_SECONDS = 60

SENSITIVITY_RISK: dict[str, int] = {
    "low": 0,
    "medium": 10,
    "high": 20,
    "critical": 30,
}


@dataclass
class ExfilFinding:
    exfil_type: str
    resource: str
    tool: str
    bytes_read: int
    event_count: int
    window_seconds: int
    sensitivity: str
    risk_score: int
    description: str


def compute_exfil_risk_score(
    exfil_type: str,
    bytes_read: int = 0,
    event_count: int = 0,
    sensitivity: str = "",
) -> int:
    """Deterministic 0-100 exfiltration risk score."""
    score = EXFIL_TYPE_BASE_RISK.get(exfil_type, 40)
    score += SENSITIVITY_RISK.get(sensitivity, 0)
    if bytes_read >= 100 * 1024 * 1024:
        score += 15
    elif bytes_read >= 50 * 1024 * 1024:
        score += 10
    if event_count >= 100:
        score += 10
    elif event_count >= 50:
        score += 5
    return max(0, min(100, score))


def detect_large_read(
    agent_id: uuid.UUID,
    resource: str,
    tool: str,
    bytes_read: int,
    threshold: int = LARGE_READ_THRESHOLD_BYTES,
) -> ExfilFinding | None:
    if bytes_read < threshold:
        return None
    risk = compute_exfil_risk_score("large_read", bytes_read=bytes_read)
    return ExfilFinding(
        exfil_type="large_read",
        resource=resource,
        tool=tool,
        bytes_read=bytes_read,
        event_count=1,
        window_seconds=0,
        sensitivity="",
        risk_score=risk,
        description=f"Agent {agent_id} read {bytes_read} bytes from {resource} in a single operation",
    )


def detect_rapid_read(
    agent_id: uuid.UUID,
    resource: str,
    tool: str,
    event_count: int,
    window_seconds: int,
    threshold: int = RAPID_READ_EVENT_THRESHOLD,
) -> ExfilFinding | None:
    if event_count < threshold or window_seconds <= 0:
        return None
    risk = compute_exfil_risk_score("rapid_read", event_count=event_count)
    return ExfilFinding(
        exfil_type="rapid_read",
        resource=resource,
        tool=tool,
        bytes_read=0,
        event_count=event_count,
        window_seconds=window_seconds,
        sensitivity="",
        risk_score=risk,
        description=(
            f"Agent {agent_id} performed {event_count} reads on {resource} in {window_seconds}s"
        ),
    )


def detect_sensitive_boundary_exit(
    agent_id: uuid.UUID,
    resource: str,
    tool: str,
    sensitivity: str,
    external_service: str,
) -> ExfilFinding | None:
    if not sensitivity or sensitivity == "low":
        return None
    if not external_service:
        return None
    lowered = external_service.lower()
    if any(vendor in lowered for vendor in TRUSTED_EXTERNAL_SERVICES):
        return None
    risk = compute_exfil_risk_score("sensitive_boundary_exit", sensitivity=sensitivity)
    return ExfilFinding(
        exfil_type="sensitive_boundary_exit",
        resource=resource,
        tool=tool,
        bytes_read=0,
        event_count=1,
        window_seconds=0,
        sensitivity=sensitivity,
        risk_score=risk,
        description=(
            f"Agent {agent_id} sent {sensitivity}-sensitive data from {resource} to {external_service}"
        ),
    )


def exfil_to_dict(event: ExfiltrationEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "tenant_id": str(event.tenant_id),
        "agent_id": str(event.agent_id) if event.agent_id else None,
        "endpoint_id": str(event.endpoint_id) if event.endpoint_id else None,
        "exfil_type": event.exfil_type,
        "resource": event.resource,
        "tool": event.tool,
        "bytes_read": event.bytes_read,
        "event_count": event.event_count,
        "window_seconds": event.window_seconds,
        "sensitivity": event.sensitivity,
        "risk_score": event.risk_score,
        "risk_band": risk_band(event.risk_score),
        "status": event.status,
        "source_event_ids": event.source_event_ids or [],
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


async def list_exfil_events(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    status: str | None = None,
    exfil_type: str | None = None,
) -> list[ExfiltrationEvent]:
    stmt = select(ExfiltrationEvent).where(ExfiltrationEvent.tenant_id == tenant_id)
    if status and status != "all":
        stmt = stmt.where(ExfiltrationEvent.status == status)
    if exfil_type and exfil_type != "all":
        stmt = stmt.where(ExfiltrationEvent.exfil_type == exfil_type)
    stmt = stmt.order_by(ExfiltrationEvent.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def acknowledge_exfil(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    exfil_id: uuid.UUID,
) -> ExfiltrationEvent | None:
    result = await db.execute(
        select(ExfiltrationEvent).where(
            ExfiltrationEvent.tenant_id == tenant_id,
            ExfiltrationEvent.id == exfil_id,
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        return None
    event.status = "acknowledged"
    await db.flush()
    return event


async def exfil_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    events = (
        await db.execute(
            select(ExfiltrationEvent).where(ExfiltrationEvent.tenant_id == tenant_id)
        )
    ).scalars().all()
    open_events = [e for e in events if e.status == "open"]
    by_type: dict[str, int] = {}
    high_risk = 0
    for event in open_events:
        by_type[event.exfil_type] = by_type.get(event.exfil_type, 0) + 1
        if event.risk_score >= 60:
            high_risk += 1
    return {
        "total": len(events),
        "open": len(open_events),
        "high_risk": high_risk,
        "by_type": by_type,
    }
