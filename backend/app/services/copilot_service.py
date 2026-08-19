"""Microsoft Copilot governance: connector/instance risk, sync adapter, drift (Phase 4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.copilot import (
    CopilotBaseline,
    CopilotConnector,
    CopilotDriftRecord,
    CopilotInstance,
)
from app.services.agentic_service import SENSITIVE_DATA_KEYWORDS, risk_band

# Base risk per connector type (0-100 scale).
CONNECTOR_TYPE_BASE_RISK: dict[str, int] = {
    "power_platform": 35,
    "graph": 25,
    "custom": 50,
}

# Base risk per Copilot instance type.
COPILOT_INSTANCE_BASE_RISK: dict[str, int] = {
    "m365_copilot": 30,
    "copilot_studio_agent": 35,
    "teams": 25,
}

# Auth types that are riskier than OAuth.
RISKY_AUTH_TYPES: set[str] = {"api_key", "certificate", "basic", "none"}

# Broad permission markers that raise risk.
BROAD_PERMISSION_MARKERS: set[str] = {
    "admin",
    "root",
    "sudo",
    "write",
    "delete",
    "all",
    "mail.readwrite",
    "files.readwrite",
    "user.readwrite",
    "group.readwrite",
}

DRIFT_TYPES = {"risk_increase", "risk_decrease", "policy_mismatch", "new_entity", "removed_entity"}


def _sensitive_contribution(items: list[str] | None) -> int:
    total = 0
    for item in items or []:
        lowered = item.lower()
        for keyword, weight in SENSITIVE_DATA_KEYWORDS.items():
            if keyword in lowered:
                total += weight
                break
    return total


def _broad_permission_contribution(permissions: list[str] | None) -> int:
    lowered = {p.lower() for p in permissions or []}
    if lowered & BROAD_PERMISSION_MARKERS:
        return 15
    return 0


def compute_connector_risk_score(
    connector_type: str,
    auth_type: str = "",
    scopes: list[str] | None = None,
    data_sources: list[str] | None = None,
    permissions: list[str] | None = None,
) -> int:
    """Deterministic 0-100 connector risk score.

    Base by connector type (custom connectors are riskiest) plus bounded
    contributions from risky auth, sensitive scopes/data sources, and broad
    permissions. Reuses the control-plane risk conventions.
    """
    score = CONNECTOR_TYPE_BASE_RISK.get(connector_type, 30)
    if auth_type.lower() in RISKY_AUTH_TYPES:
        score += 15
    score += _sensitive_contribution(scopes)
    score += _sensitive_contribution(data_sources)
    score += _broad_permission_contribution(permissions)
    return max(0, min(100, score))


def compute_copilot_instance_risk_score(
    instance_type: str,
    data_sources: list[str] | None = None,
    permissions: list[str] | None = None,
) -> int:
    """Deterministic 0-100 Copilot instance risk score."""
    score = COPILOT_INSTANCE_BASE_RISK.get(instance_type, 30)
    score += _sensitive_contribution(data_sources)
    score += _broad_permission_contribution(permissions)
    return max(0, min(100, score))


def instance_to_dict(instance: CopilotInstance) -> dict[str, Any]:
    return {
        "id": str(instance.id),
        "tenant_id": str(instance.tenant_id),
        "external_id": instance.external_id,
        "instance_type": instance.instance_type,
        "name": instance.name,
        "display_name": instance.display_name,
        "status": instance.status,
        "risk_score": instance.risk_score,
        "risk_band": risk_band(instance.risk_score),
        "owner": instance.owner,
        "environment": instance.environment,
        "data_sources": instance.data_sources or [],
        "permissions": instance.permissions or [],
        "metadata_json": instance.metadata_json,
        "last_synced_at": instance.last_synced_at.isoformat() if instance.last_synced_at else None,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
    }


def connector_to_dict(connector: CopilotConnector) -> dict[str, Any]:
    return {
        "id": str(connector.id),
        "tenant_id": str(connector.tenant_id),
        "external_id": connector.external_id,
        "name": connector.name,
        "connector_type": connector.connector_type,
        "publisher": connector.publisher,
        "status": connector.status,
        "risk_score": connector.risk_score,
        "risk_band": connector.risk_band,
        "auth_type": connector.auth_type,
        "scopes": connector.scopes or [],
        "data_sources": connector.data_sources or [],
        "permissions": connector.permissions or [],
        "metadata_json": connector.metadata_json,
        "last_synced_at": connector.last_synced_at.isoformat() if connector.last_synced_at else None,
        "created_at": connector.created_at.isoformat() if connector.created_at else None,
        "updated_at": connector.updated_at.isoformat() if connector.updated_at else None,
    }


@dataclass
class CopilotSyncResult:
    instances_upserted: int = 0
    instances_removed: int = 0
    connectors_upserted: int = 0
    connectors_removed: int = 0
    drift_found: int = 0


async def _upsert_instance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    item: dict[str, Any],
) -> CopilotInstance:
    external_id = str(item.get("external_id") or item.get("id") or "")
    result = await db.execute(
        select(CopilotInstance).where(
            CopilotInstance.tenant_id == tenant_id,
            CopilotInstance.external_id == external_id,
        )
    )
    instance = result.scalar_one_or_none()
    instance_type = str(item.get("instance_type") or item.get("type") or "m365_copilot")
    data_sources = item.get("data_sources") or []
    permissions = item.get("permissions") or []
    risk_score = compute_copilot_instance_risk_score(instance_type, data_sources, permissions)
    now = datetime.now(UTC)
    if instance is None:
        instance = CopilotInstance(
            tenant_id=tenant_id,
            external_id=external_id,
            instance_type=instance_type,
            name=str(item.get("name") or external_id),
            display_name=str(item.get("display_name") or ""),
            status=str(item.get("status") or "active"),
            risk_score=risk_score,
            owner=str(item.get("owner") or ""),
            environment=str(item.get("environment") or ""),
            data_sources=data_sources,
            permissions=permissions,
            metadata_json=item.get("metadata") or {},
            last_synced_at=now,
        )
        db.add(instance)
    else:
        instance.instance_type = instance_type
        instance.name = str(item.get("name") or instance.name)
        instance.display_name = str(item.get("display_name") or instance.display_name)
        instance.status = str(item.get("status") or instance.status)
        instance.risk_score = risk_score
        instance.owner = str(item.get("owner") or instance.owner)
        instance.environment = str(item.get("environment") or instance.environment)
        instance.data_sources = data_sources
        instance.permissions = permissions
        instance.metadata_json = item.get("metadata") or instance.metadata_json
        instance.last_synced_at = now
    await db.flush()
    return instance


async def _upsert_connector(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    item: dict[str, Any],
) -> CopilotConnector:
    external_id = str(item.get("external_id") or item.get("id") or "")
    result = await db.execute(
        select(CopilotConnector).where(
            CopilotConnector.tenant_id == tenant_id,
            CopilotConnector.external_id == external_id,
        )
    )
    connector = result.scalar_one_or_none()
    connector_type = str(item.get("connector_type") or item.get("type") or "custom")
    auth_type = str(item.get("auth_type") or "")
    scopes = item.get("scopes") or []
    data_sources = item.get("data_sources") or []
    permissions = item.get("permissions") or []
    risk_score = compute_connector_risk_score(connector_type, auth_type, scopes, data_sources, permissions)
    now = datetime.now(UTC)
    if connector is None:
        connector = CopilotConnector(
            tenant_id=tenant_id,
            external_id=external_id,
            name=str(item.get("name") or external_id),
            connector_type=connector_type,
            publisher=str(item.get("publisher") or ""),
            status=str(item.get("status") or "active"),
            risk_score=risk_score,
            risk_band=risk_band(risk_score),
            auth_type=auth_type,
            scopes=scopes,
            data_sources=data_sources,
            permissions=permissions,
            metadata_json=item.get("metadata") or {},
            last_synced_at=now,
        )
        db.add(connector)
    else:
        connector.name = str(item.get("name") or connector.name)
        connector.connector_type = connector_type
        connector.publisher = str(item.get("publisher") or connector.publisher)
        connector.status = str(item.get("status") or connector.status)
        connector.risk_score = risk_score
        connector.risk_band = risk_band(risk_score)
        connector.auth_type = auth_type
        connector.scopes = scopes
        connector.data_sources = data_sources
        connector.permissions = permissions
        connector.metadata_json = item.get("metadata") or connector.metadata_json
        connector.last_synced_at = now
    await db.flush()
    return connector


async def sync_copilot_payload(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    payload: dict[str, Any],
) -> CopilotSyncResult:
    """Idempotently merge a tenant-provided Copilot/Graph sync payload.

    Upserts instances and connectors by ``(tenant_id, external_id)`` and
    soft-deletes (``status="removed"``) any previously-synced entity that is no
    longer present in the payload. Does not call MS Graph — the tenant's sync
    job provides the payload.
    """
    result = CopilotSyncResult()

    instance_items = payload.get("instances") or []
    seen_instance_ids: set[str] = set()
    for item in instance_items:
        if not isinstance(item, dict):
            continue
        external_id = str(item.get("external_id") or item.get("id") or "")
        if not external_id:
            continue
        seen_instance_ids.add(external_id)
        await _upsert_instance(db, tenant_id, item)
        result.instances_upserted += 1

    connector_items = payload.get("connectors") or []
    seen_connector_ids: set[str] = set()
    for item in connector_items:
        if not isinstance(item, dict):
            continue
        external_id = str(item.get("external_id") or item.get("id") or "")
        if not external_id:
            continue
        seen_connector_ids.add(external_id)
        await _upsert_connector(db, tenant_id, item)
        result.connectors_upserted += 1

    existing_instances = (
        await db.execute(
            select(CopilotInstance).where(
                CopilotInstance.tenant_id == tenant_id,
                CopilotInstance.status != "removed",
            )
        )
    ).scalars().all()
    for instance in existing_instances:
        if instance.external_id not in seen_instance_ids:
            instance.status = "removed"
            result.instances_removed += 1

    existing_connectors = (
        await db.execute(
            select(CopilotConnector).where(
                CopilotConnector.tenant_id == tenant_id,
                CopilotConnector.status != "removed",
            )
        )
    ).scalars().all()
    for connector in existing_connectors:
        if connector.external_id not in seen_connector_ids:
            connector.status = "removed"
            result.connectors_removed += 1

    await db.flush()
    return result


async def capture_baseline(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    name: str = "",
    created_by: str = "",
) -> CopilotBaseline:
    instances = (
        await db.execute(
            select(CopilotInstance).where(
                CopilotInstance.tenant_id == tenant_id,
                CopilotInstance.status != "removed",
            )
        )
    ).scalars().all()
    connectors = (
        await db.execute(
            select(CopilotConnector).where(
                CopilotConnector.tenant_id == tenant_id,
                CopilotConnector.status != "removed",
            )
        )
    ).scalars().all()
    snapshot = {
        "instances": [instance_to_dict(instance) for instance in instances],
        "connectors": [connector_to_dict(connector) for connector in connectors],
    }
    baseline = CopilotBaseline(
        tenant_id=tenant_id,
        name=name,
        created_by=created_by,
        snapshot=snapshot,
    )
    db.add(baseline)
    await db.flush()
    return baseline


def _severity_for_delta(delta: int) -> str:
    if delta >= 20:
        return "critical"
    if delta >= 10:
        return "high"
    return "medium"


def compare_state_to_baseline(
    baseline_snapshot: dict[str, Any],
    current_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Pure comparison of current state against a baseline snapshot.

    Returns a list of drift finding dicts (no DB access), so it is unit-testable
    without a session. Each finding carries entity_type, entity_external_id,
    entity_name, drift_type, severity, previous_value, current_value, description.
    """
    findings: list[dict[str, Any]] = []

    baseline_instances = {i["external_id"]: i for i in baseline_snapshot.get("instances") or []}
    baseline_connectors = {c["external_id"]: c for c in baseline_snapshot.get("connectors") or []}
    current_instances = {i["external_id"]: i for i in current_state.get("instances") or []}
    current_connectors = {c["external_id"]: c for c in current_state.get("connectors") or []}

    for entity_type, baseline_map, current_map in (
        ("instance", baseline_instances, current_instances),
        ("connector", baseline_connectors, current_connectors),
    ):
        for external_id, baseline in baseline_map.items():
            current = current_map.get(external_id)
            if current is None:
                findings.append(
                    {
                        "entity_type": entity_type,
                        "entity_external_id": external_id,
                        "entity_name": baseline.get("name", ""),
                        "drift_type": "removed_entity",
                        "severity": "medium",
                        "previous_value": baseline,
                        "current_value": None,
                        "description": f"{entity_type} '{baseline.get('name', external_id)}' is no longer present",
                    }
                )
                continue
            baseline_risk = int(baseline.get("risk_score") or 0)
            current_risk = int(current.get("risk_score") or 0)
            if current_risk > baseline_risk:
                findings.append(
                    {
                        "entity_type": entity_type,
                        "entity_external_id": external_id,
                        "entity_name": current.get("name", ""),
                        "drift_type": "risk_increase",
                        "severity": _severity_for_delta(current_risk - baseline_risk),
                        "previous_value": {"risk_score": baseline_risk},
                        "current_value": {"risk_score": current_risk},
                        "description": (
                            f"{entity_type} '{current.get('name', external_id)}' risk increased "
                            f"from {baseline_risk} to {current_risk}"
                        ),
                    }
                )
            elif current_risk < baseline_risk:
                findings.append(
                    {
                        "entity_type": entity_type,
                        "entity_external_id": external_id,
                        "entity_name": current.get("name", ""),
                        "drift_type": "risk_decrease",
                        "severity": "low",
                        "previous_value": {"risk_score": baseline_risk},
                        "current_value": {"risk_score": current_risk},
                        "description": (
                            f"{entity_type} '{current.get('name', external_id)}' risk decreased "
                            f"from {baseline_risk} to {current_risk}"
                        ),
                    }
                )
            if baseline.get("status") != current.get("status"):
                findings.append(
                    {
                        "entity_type": entity_type,
                        "entity_external_id": external_id,
                        "entity_name": current.get("name", ""),
                        "drift_type": "policy_mismatch",
                        "severity": "medium",
                        "previous_value": {"status": baseline.get("status")},
                        "current_value": {"status": current.get("status")},
                        "description": (
                            f"{entity_type} '{current.get('name', external_id)}' status changed "
                            f"from '{baseline.get('status')}' to '{current.get('status')}'"
                        ),
                    }
                )
        for external_id, current in current_map.items():
            if external_id not in baseline_map:
                findings.append(
                    {
                        "entity_type": entity_type,
                        "entity_external_id": external_id,
                        "entity_name": current.get("name", ""),
                        "drift_type": "new_entity",
                        "severity": "low",
                        "previous_value": None,
                        "current_value": current,
                        "description": f"new {entity_type} '{current.get('name', external_id)}' detected",
                    }
                )

    return findings


async def _current_state(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    instances = (
        await db.execute(
            select(CopilotInstance).where(
                CopilotInstance.tenant_id == tenant_id,
                CopilotInstance.status != "removed",
            )
        )
    ).scalars().all()
    connectors = (
        await db.execute(
            select(CopilotConnector).where(
                CopilotConnector.tenant_id == tenant_id,
                CopilotConnector.status != "removed",
            )
        )
    ).scalars().all()
    return {
        "instances": [instance_to_dict(instance) for instance in instances],
        "connectors": [connector_to_dict(connector) for connector in connectors],
    }


async def detect_drift(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    baseline_id: uuid.UUID | None = None,
) -> list[CopilotDriftRecord]:
    """Compare current state against a baseline and persist new drift findings.

    Uses the most recent baseline when ``baseline_id`` is not provided. Skips
    findings that already have an identical open record for the same entity.
    """
    if baseline_id is None:
        result = await db.execute(
            select(CopilotBaseline)
            .where(CopilotBaseline.tenant_id == tenant_id)
            .order_by(CopilotBaseline.created_at.desc())
            .limit(1)
        )
        baseline = result.scalar_one_or_none()
    else:
        baseline = await db.get(CopilotBaseline, baseline_id)
    if baseline is None or not baseline.snapshot:
        return []

    current = await _current_state(db, tenant_id)
    findings = compare_state_to_baseline(baseline.snapshot, current)

    created: list[CopilotDriftRecord] = []
    for finding in findings:
        existing = await db.execute(
            select(CopilotDriftRecord.id).where(
                CopilotDriftRecord.tenant_id == tenant_id,
                CopilotDriftRecord.entity_external_id == finding["entity_external_id"],
                CopilotDriftRecord.drift_type == finding["drift_type"],
                CopilotDriftRecord.status == "open",
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue
        record = CopilotDriftRecord(
            tenant_id=tenant_id,
            baseline_id=baseline.id,
            entity_type=finding["entity_type"],
            entity_external_id=finding["entity_external_id"],
            entity_name=finding["entity_name"],
            drift_type=finding["drift_type"],
            severity=finding["severity"],
            previous_value=finding["previous_value"],
            current_value=finding["current_value"],
            description=finding["description"],
            status="open",
        )
        db.add(record)
        created.append(record)
    await db.flush()
    return created


async def list_drift(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    status: str | None = None,
    severity: str | None = None,
) -> list[CopilotDriftRecord]:
    stmt = select(CopilotDriftRecord).where(CopilotDriftRecord.tenant_id == tenant_id)
    if status and status != "all":
        stmt = stmt.where(CopilotDriftRecord.status == status)
    if severity and severity != "all":
        stmt = stmt.where(CopilotDriftRecord.severity == severity)
    stmt = stmt.order_by(CopilotDriftRecord.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def acknowledge_drift(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    drift_id: uuid.UUID,
) -> CopilotDriftRecord | None:
    result = await db.execute(
        select(CopilotDriftRecord).where(
            CopilotDriftRecord.tenant_id == tenant_id,
            CopilotDriftRecord.id == drift_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None
    record.status = "acknowledged"
    await db.flush()
    return record


def drift_to_dict(record: CopilotDriftRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "tenant_id": str(record.tenant_id),
        "baseline_id": str(record.baseline_id) if record.baseline_id else None,
        "entity_type": record.entity_type,
        "entity_id": str(record.entity_id) if record.entity_id else None,
        "entity_external_id": record.entity_external_id,
        "entity_name": record.entity_name,
        "drift_type": record.drift_type,
        "severity": record.severity,
        "previous_value": record.previous_value,
        "current_value": record.current_value,
        "description": record.description,
        "status": record.status,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "resolved_at": record.resolved_at.isoformat() if record.resolved_at else None,
    }


async def copilot_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    instances = (
        await db.execute(
            select(CopilotInstance).where(
                CopilotInstance.tenant_id == tenant_id,
                CopilotInstance.status != "removed",
            )
        )
    ).scalars().all()
    connectors = (
        await db.execute(
            select(CopilotConnector).where(
                CopilotConnector.tenant_id == tenant_id,
                CopilotConnector.status != "removed",
            )
        )
    ).scalars().all()
    drift = (
        await db.execute(
            select(CopilotDriftRecord).where(
                CopilotDriftRecord.tenant_id == tenant_id,
                CopilotDriftRecord.status == "open",
            )
        )
    ).scalars().all()

    instances_by_type: dict[str, int] = {}
    high_risk_instances = 0
    for instance in instances:
        instances_by_type[instance.instance_type] = instances_by_type.get(instance.instance_type, 0) + 1
        if instance.risk_score >= 60:
            high_risk_instances += 1

    connectors_by_type: dict[str, int] = {}
    high_risk_connectors = 0
    for connector in connectors:
        connectors_by_type[connector.connector_type] = connectors_by_type.get(connector.connector_type, 0) + 1
        if connector.risk_score >= 60:
            high_risk_connectors += 1

    by_severity: dict[str, int] = {}
    for record in drift:
        by_severity[record.severity] = by_severity.get(record.severity, 0) + 1

    return {
        "instances_total": len(instances),
        "instances_by_type": instances_by_type,
        "connectors_total": len(connectors),
        "connectors_by_type": connectors_by_type,
        "high_risk_instances": high_risk_instances,
        "high_risk_connectors": high_risk_connectors,
        "open_drift": len(drift),
        "by_severity": by_severity,
    }
