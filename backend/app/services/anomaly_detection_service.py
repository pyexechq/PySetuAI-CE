"""Agentic anomaly detection (Phase 5).

Pure, deterministic detectors (unit-testable without a DB) plus async
persistence helpers that mirror the Copilot drift-detection pattern.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agentic import AgentAnomalyRecord
from app.services.agentic_service import SENSITIVE_DATA_KEYWORDS, risk_band

# Base risk contribution per anomaly type (0-100 scale).
ANOMALY_TYPE_BASE_RISK: dict[str, int] = {
    "unusual_tool_usage": 30,
    "unusual_data_access": 40,
    "unusual_volume": 35,
    "unusual_timing": 20,
    "unusual_chain_risk": 45,
}

SEVERITY_RISK: dict[str, int] = {
    "low": 0,
    "medium": 10,
    "high": 20,
    "critical": 30,
}

# Volume anomaly: observed count must exceed baseline by this multiplier.
VOLUME_ANOMALY_MULTIPLIER = 3.0
# Minimum absolute delta for a volume anomaly when baseline is small.
VOLUME_ANOMALY_MIN_DELTA = 5

# Timing anomaly: hours outside this set are considered unusual.
USUAL_HOURS: set[int] = set(range(6, 22))


@dataclass
class AnomalyFinding:
    anomaly_type: str
    severity: str
    risk_score: int
    baseline_value: dict[str, Any]
    observed_value: dict[str, Any]
    description: str


def compute_anomaly_risk_score(
    anomaly_type: str,
    severity: str,
    agent_risk: int = 0,
    delta: int = 0,
) -> int:
    """Deterministic 0-100 anomaly risk score."""
    score = ANOMALY_TYPE_BASE_RISK.get(anomaly_type, 30)
    score += SEVERITY_RISK.get(severity, 10)
    score += max(0, min(15, agent_risk // 7))
    score += max(0, min(10, delta // 10))
    return max(0, min(100, score))


def detect_volume_anomaly(
    agent_id: uuid.UUID,
    event_count: int,
    window_seconds: int,
    baseline_count: int,
) -> AnomalyFinding | None:
    if baseline_count <= 0:
        return None
    if event_count >= baseline_count * VOLUME_ANOMALY_MULTIPLIER and (
        event_count - baseline_count >= VOLUME_ANOMALY_MIN_DELTA
    ):
        severity = "high" if event_count >= baseline_count * 5 else "medium"
        risk = compute_anomaly_risk_score("unusual_volume", severity, delta=event_count - baseline_count)
        return AnomalyFinding(
            anomaly_type="unusual_volume",
            severity=severity,
            risk_score=risk,
            baseline_value={"event_count": baseline_count, "window_seconds": window_seconds},
            observed_value={"event_count": event_count, "window_seconds": window_seconds},
            description=(
                f"Agent {agent_id} produced {event_count} events in {window_seconds}s "
                f"vs baseline {baseline_count}"
            ),
        )
    return None


def detect_tool_usage_anomaly(
    agent_id: uuid.UUID,
    tool_counts: dict[str, int],
    baseline_tools: set[str],
) -> AnomalyFinding | None:
    new_tools = [tool for tool in tool_counts if tool not in baseline_tools]
    if not new_tools:
        return None
    severity = "high" if len(new_tools) >= 3 else "medium"
    risk = compute_anomaly_risk_score("unusual_tool_usage", severity)
    return AnomalyFinding(
        anomaly_type="unusual_tool_usage",
        severity=severity,
        risk_score=risk,
        baseline_value={"tools": sorted(baseline_tools)},
        observed_value={"new_tools": sorted(new_tools)},
        description=f"Agent {agent_id} used tools not in baseline: {', '.join(sorted(new_tools))}",
    )


def detect_data_access_anomaly(
    agent_id: uuid.UUID,
    resources: list[str],
    baseline_resources: set[str],
) -> AnomalyFinding | None:
    new_resources = [r for r in resources if r not in baseline_resources]
    sensitive_new = [
        r
        for r in new_resources
        if any(keyword in r.lower() for keyword in SENSITIVE_DATA_KEYWORDS)
    ]
    if not sensitive_new:
        return None
    severity = "critical" if len(sensitive_new) >= 2 else "high"
    risk = compute_anomaly_risk_score("unusual_data_access", severity)
    return AnomalyFinding(
        anomaly_type="unusual_data_access",
        severity=severity,
        risk_score=risk,
        baseline_value={"resources": sorted(baseline_resources)},
        observed_value={"sensitive_new_resources": sorted(sensitive_new)},
        description=(
            f"Agent {agent_id} accessed sensitive resources outside baseline: "
            f"{', '.join(sorted(sensitive_new))}"
        ),
    )


def detect_timing_anomaly(
    agent_id: uuid.UUID,
    hour_distribution: dict[int, int],
    baseline_hours: set[int],
) -> AnomalyFinding | None:
    unusual_hours = [hour for hour, count in hour_distribution.items() if hour not in baseline_hours and count > 0]
    if not unusual_hours:
        return None
    severity = "medium"
    risk = compute_anomaly_risk_score("unusual_timing", severity)
    return AnomalyFinding(
        anomaly_type="unusual_timing",
        severity=severity,
        risk_score=risk,
        baseline_value={"hours": sorted(baseline_hours)},
        observed_value={"unusual_hours": sorted(unusual_hours)},
        description=f"Agent {agent_id} active in unusual hours: {', '.join(str(h) for h in sorted(unusual_hours))}",
    )


def detect_chain_risk_anomaly(
    agent_id: uuid.UUID,
    chain_risk_scores: list[int],
    baseline_avg: float,
) -> AnomalyFinding | None:
    if not chain_risk_scores:
        return None
    avg = sum(chain_risk_scores) / len(chain_risk_scores)
    if avg >= 60 and avg >= baseline_avg + 15:
        severity = "critical" if avg >= 80 else "high"
        risk = compute_anomaly_risk_score("unusual_chain_risk", severity, delta=int(avg - baseline_avg))
        return AnomalyFinding(
            anomaly_type="unusual_chain_risk",
            severity=severity,
            risk_score=risk,
            baseline_value={"avg_chain_risk": baseline_avg},
            observed_value={"avg_chain_risk": round(avg, 1), "count": len(chain_risk_scores)},
            description=(
                f"Agent {agent_id} sustained chain risk {avg:.0f} vs baseline {baseline_avg:.0f}"
            ),
        )
    return None


def anomaly_to_dict(record: AgentAnomalyRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "tenant_id": str(record.tenant_id),
        "agent_id": str(record.agent_id) if record.agent_id else None,
        "endpoint_id": str(record.endpoint_id) if record.endpoint_id else None,
        "anomaly_type": record.anomaly_type,
        "severity": record.severity,
        "risk_score": record.risk_score,
        "risk_band": risk_band(record.risk_score),
        "baseline_value": record.baseline_value,
        "observed_value": record.observed_value,
        "description": record.description,
        "status": record.status,
        "source_event_ids": record.source_event_ids or [],
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
    }


async def list_anomalies(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    status: str | None = None,
    severity: str | None = None,
    anomaly_type: str | None = None,
) -> list[AgentAnomalyRecord]:
    stmt = select(AgentAnomalyRecord).where(AgentAnomalyRecord.tenant_id == tenant_id)
    if status and status != "all":
        stmt = stmt.where(AgentAnomalyRecord.status == status)
    if severity and severity != "all":
        stmt = stmt.where(AgentAnomalyRecord.severity == severity)
    if anomaly_type and anomaly_type != "all":
        stmt = stmt.where(AgentAnomalyRecord.anomaly_type == anomaly_type)
    stmt = stmt.order_by(AgentAnomalyRecord.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def acknowledge_anomaly(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    anomaly_id: uuid.UUID,
) -> AgentAnomalyRecord | None:
    result = await db.execute(
        select(AgentAnomalyRecord).where(
            AgentAnomalyRecord.tenant_id == tenant_id,
            AgentAnomalyRecord.id == anomaly_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None
    record.status = "acknowledged"
    record.resolved_at = datetime.now(UTC)
    await db.flush()
    return record


async def anomaly_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    records = (
        await db.execute(
            select(AgentAnomalyRecord).where(AgentAnomalyRecord.tenant_id == tenant_id)
        )
    ).scalars().all()
    open_records = [r for r in records if r.status == "open"]
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    high_risk = 0
    for record in open_records:
        by_type[record.anomaly_type] = by_type.get(record.anomaly_type, 0) + 1
        by_severity[record.severity] = by_severity.get(record.severity, 0) + 1
        if record.risk_score >= 60:
            high_risk += 1
    return {
        "total": len(records),
        "open": len(open_records),
        "high_risk": high_risk,
        "by_type": by_type,
        "by_severity": by_severity,
    }
