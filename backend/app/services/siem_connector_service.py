"""CRUD and push delivery for external SIEM connectors."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog, SiemConnector
from app.services.integration_service import mask_secret
from app.services.siem_export_service import audit_log_to_dict, format_cef, format_elastic_ndjson

VALID_CONNECTOR_TYPES = frozenset({"splunk_hec", "elastic", "azure_sentinel", "webhook"})
VALID_EXPORT_FORMATS = frozenset({"json", "cef", "ndjson", "elastic_bulk"})
MAX_EXPORT_BATCH = 500


@dataclass
class SiemExportResult:
    exported: int
    connector_id: str
    connector_name: str
    message: str


def connector_to_dict(connector: SiemConnector, *, include_token: bool = False) -> dict:
    return {
        "id": str(connector.id),
        "name": connector.name,
        "connector_type": connector.connector_type,
        "endpoint_url": connector.endpoint_url,
        "export_format": connector.export_format,
        "enabled": connector.enabled,
        "events_exported": connector.events_exported,
        "last_export_at": connector.last_export_at.isoformat() if connector.last_export_at else None,
        "last_error": connector.last_error or "",
        "auth_token_set": bool(connector.auth_token),
        "auth_token_masked": mask_secret(connector.auth_token) if connector.auth_token else None,
        **({"auth_token": connector.auth_token} if include_token else {}),
    }


async def list_connectors(db: AsyncSession, tenant_id: uuid.UUID) -> list[SiemConnector]:
    result = await db.execute(
        select(SiemConnector).where(SiemConnector.tenant_id == tenant_id).order_by(SiemConnector.created_at.desc())
    )
    return list(result.scalars().all())


async def get_connector(db: AsyncSession, tenant_id: uuid.UUID, connector_id: uuid.UUID) -> SiemConnector | None:
    result = await db.execute(
        select(SiemConnector).where(
            SiemConnector.tenant_id == tenant_id,
            SiemConnector.id == connector_id,
        )
    )
    return result.scalar_one_or_none()


async def create_connector(db: AsyncSession, tenant_id: uuid.UUID, data: dict) -> SiemConnector:
    connector_type = str(data.get("connector_type", "webhook")).strip().lower()
    export_format = str(data.get("export_format", "json")).strip().lower()
    if connector_type not in VALID_CONNECTOR_TYPES:
        raise ValueError(f"Invalid connector_type — use one of: {', '.join(sorted(VALID_CONNECTOR_TYPES))}")
    if export_format not in VALID_EXPORT_FORMATS:
        raise ValueError(f"Invalid export_format — use one of: {', '.join(sorted(VALID_EXPORT_FORMATS))}")

    connector = SiemConnector(
        tenant_id=tenant_id,
        name=str(data["name"]).strip()[:255],
        connector_type=connector_type,
        endpoint_url=str(data["endpoint_url"]).strip()[:1024],
        auth_token=(str(data["auth_token"]).strip() or None) if data.get("auth_token") else None,
        export_format=export_format,
        enabled=bool(data.get("enabled", True)),
    )
    db.add(connector)
    await db.commit()
    await db.refresh(connector)
    return connector


async def update_connector(
    db: AsyncSession,
    connector: SiemConnector,
    data: dict,
) -> SiemConnector:
    if "name" in data and data["name"] is not None:
        connector.name = str(data["name"]).strip()[:255]
    if "connector_type" in data and data["connector_type"] is not None:
        connector_type = str(data["connector_type"]).strip().lower()
        if connector_type not in VALID_CONNECTOR_TYPES:
            raise ValueError(f"Invalid connector_type — use one of: {', '.join(sorted(VALID_CONNECTOR_TYPES))}")
        connector.connector_type = connector_type
    if "endpoint_url" in data and data["endpoint_url"] is not None:
        connector.endpoint_url = str(data["endpoint_url"]).strip()[:1024]
    if "export_format" in data and data["export_format"] is not None:
        export_format = str(data["export_format"]).strip().lower()
        if export_format not in VALID_EXPORT_FORMATS:
            raise ValueError(f"Invalid export_format — use one of: {', '.join(sorted(VALID_EXPORT_FORMATS))}")
        connector.export_format = export_format
    if "enabled" in data and data["enabled"] is not None:
        connector.enabled = bool(data["enabled"])
    if "auth_token" in data and data["auth_token"] is not None:
        token = str(data["auth_token"]).strip()
        connector.auth_token = token or None
    await db.commit()
    await db.refresh(connector)
    return connector


async def delete_connector(db: AsyncSession, connector: SiemConnector) -> None:
    await db.delete(connector)
    await db.commit()


async def fetch_logs_for_export(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    since: datetime | None = None,
    limit: int = MAX_EXPORT_BATCH,
) -> list[AuditLog]:
    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id).order_by(AuditLog.timestamp.asc()).limit(limit)
    if since is not None:
        query = query.where(AuditLog.timestamp > since)
    result = await db.execute(query)
    return list(result.scalars().all())


def _build_headers(connector: SiemConnector) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "User-Agent": "PySetu-SIEM/0.1"}
    token = connector.auth_token or ""
    if connector.connector_type == "splunk_hec":
        headers["Authorization"] = f"Splunk {token}" if token else ""
    elif connector.connector_type == "azure_sentinel":
        if token:
            headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"
    elif connector.connector_type == "elastic":
        if token:
            headers["Authorization"] = f"ApiKey {token}"
    elif token:
        headers["Authorization"] = f"Bearer {token}"
    return {k: v for k, v in headers.items() if v}


def _build_payload(connector: SiemConnector, logs: list[AuditLog]) -> tuple[str, dict[str, str], str | bytes]:
    headers = _build_headers(connector)
    fmt = connector.export_format

    if connector.connector_type == "splunk_hec":
        events = [{"event": audit_log_to_dict(log), "sourcetype": "pysetu:audit"} for log in logs]
        return json.dumps(events), headers, "application/json"

    if connector.connector_type == "elastic" or fmt == "elastic_bulk":
        headers["Content-Type"] = "application/x-ndjson"
        return format_elastic_ndjson(logs), headers, "application/x-ndjson"

    if fmt == "cef":
        body = "\n".join(format_cef(log) for log in logs)
        headers["Content-Type"] = "text/plain"
        return body, headers, "text/plain"

    if fmt == "ndjson":
        body = "\n".join(json.dumps(audit_log_to_dict(log), separators=(",", ":")) for log in logs)
        headers["Content-Type"] = "application/x-ndjson"
        return body, headers, "application/x-ndjson"

    return json.dumps([audit_log_to_dict(log) for log in logs]), headers, "application/json"


async def push_logs_to_connector(connector: SiemConnector, logs: list[AuditLog]) -> None:
    if not logs:
        return
    body, headers, content_type = _build_payload(connector, logs)
    headers["Content-Type"] = content_type
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(connector.endpoint_url, content=body, headers=headers)
        response.raise_for_status()


async def run_connector_export(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    connector: SiemConnector,
    *,
    since: datetime | None = None,
    limit: int = MAX_EXPORT_BATCH,
) -> SiemExportResult:
    if not connector.enabled:
        raise ValueError("Connector is disabled")

    since_dt = since or connector.last_export_at
    logs = await fetch_logs_for_export(db, tenant_id, since=since_dt, limit=limit)
    if not logs:
        return SiemExportResult(
            exported=0,
            connector_id=str(connector.id),
            connector_name=connector.name,
            message="No new audit events to export",
        )

    try:
        await push_logs_to_connector(connector, logs)
        connector.events_exported += len(logs)
        connector.last_export_at = logs[-1].timestamp or datetime.now(UTC)
        connector.last_error = ""
        await db.commit()
        return SiemExportResult(
            exported=len(logs),
            connector_id=str(connector.id),
            connector_name=connector.name,
            message=f"Exported {len(logs)} event(s) to {connector.connector_type}",
        )
    except httpx.HTTPError as exc:
        connector.last_error = str(exc)
        await db.commit()
        raise


async def export_all_enabled_connectors(db: AsyncSession) -> list[SiemExportResult]:
    result = await db.execute(select(SiemConnector).where(SiemConnector.enabled.is_(True)))
    connectors = list(result.scalars().all())
    outcomes: list[SiemExportResult] = []
    for connector in connectors:
        try:
            outcomes.append(await run_connector_export(db, connector.tenant_id, connector))
        except httpx.HTTPError:
            continue
    return outcomes
