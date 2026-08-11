"""Normalize and persist externally sourced audit events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog

VALID_STATUSES = frozenset({"allowed", "blocked", "review"})
VALID_RISKS = frozenset({"low", "medium", "high", "critical"})
MAX_SYNC_BATCH = 200
MAX_ASYNC_BATCH = 5000


@dataclass
class AuditIngestEventInput:
    actor: str
    action: str
    resource: str
    status: str
    risk: str = "low"
    details: str = ""
    timestamp: datetime | None = None
    source: str = "external"
    external_id: str | None = None
    trace_id: str | None = None


@dataclass
class AuditIngestResult:
    accepted: int
    skipped: int
    duplicates: int
    ids: list[str]


def _normalize_event(raw: dict) -> AuditIngestEventInput:
    status = str(raw.get("status", "")).strip().lower()
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}' — must be one of: {', '.join(sorted(VALID_STATUSES))}")

    risk = str(raw.get("risk", "low")).strip().lower()
    if risk not in VALID_RISKS:
        raise ValueError(f"Invalid risk '{risk}' — must be one of: {', '.join(sorted(VALID_RISKS))}")

    actor = str(raw.get("actor", "")).strip()
    action = str(raw.get("action", "")).strip()
    resource = str(raw.get("resource", "")).strip()
    if not actor or not action or not resource:
        raise ValueError("actor, action, and resource are required")

    timestamp = raw.get("timestamp")
    parsed_ts: datetime | None = None
    if timestamp is not None:
        if isinstance(timestamp, datetime):
            parsed_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        else:
            parsed_ts = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if parsed_ts.tzinfo is None:
                parsed_ts = parsed_ts.replace(tzinfo=UTC)

    source = str(raw.get("source", "external")).strip() or "external"
    external_id_raw = raw.get("external_id")
    external_id = str(external_id_raw).strip() if external_id_raw else None

    details = str(raw.get("details", "")).strip()
    trace_id = raw.get("trace_id")
    if trace_id:
        trace_prefix = f"trace_id={trace_id}"
        details = f"{trace_prefix}; {details}" if details else trace_prefix

    return AuditIngestEventInput(
        actor=actor[:255],
        action=action[:100],
        resource=resource[:255],
        status=status,
        risk=risk,
        details=details,
        timestamp=parsed_ts,
        source=source[:64],
        external_id=external_id[:255] if external_id else None,
        trace_id=str(trace_id) if trace_id else None,
    )


async def _existing_external_ids(
    db: AsyncSession,
    tenant_id: UUID,
    source: str,
    external_ids: list[str],
) -> set[str]:
    if not external_ids:
        return set()
    result = await db.execute(
        select(AuditLog.external_id).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.source == source,
            AuditLog.external_id.in_(external_ids),
        )
    )
    return {row for (row,) in result.all() if row}


async def ingest_audit_events(
    db: AsyncSession,
    tenant_id: UUID,
    raw_events: list[dict],
) -> AuditIngestResult:
    if not raw_events:
        return AuditIngestResult(accepted=0, skipped=0, duplicates=0, ids=[])

    if len(raw_events) > MAX_ASYNC_BATCH:
        raise ValueError(f"Batch exceeds maximum of {MAX_ASYNC_BATCH} events")

    normalized: list[AuditIngestEventInput] = []
    skipped = 0
    for raw in raw_events:
        try:
            normalized.append(_normalize_event(raw))
        except ValueError:
            skipped += 1

    by_source: dict[str, list[AuditIngestEventInput]] = {}
    for event in normalized:
        by_source.setdefault(event.source, []).append(event)

    duplicates = 0
    to_insert: list[AuditLog] = []
    for source, events in by_source.items():
        external_ids = [e.external_id for e in events if e.external_id]
        existing = await _existing_external_ids(db, tenant_id, source, external_ids)
        seen_batch: set[str] = set()
        for event in events:
            if event.external_id:
                if event.external_id in existing or event.external_id in seen_batch:
                    duplicates += 1
                    continue
                seen_batch.add(event.external_id)
            to_insert.append(
                AuditLog(
                    tenant_id=tenant_id,
                    timestamp=event.timestamp or datetime.now(UTC),
                    actor=event.actor,
                    action=event.action,
                    resource=event.resource,
                    status=event.status,
                    risk=event.risk,
                    details=event.details,
                    source=event.source,
                    external_id=event.external_id,
                )
            )

    if to_insert:
        db.add_all(to_insert)
        await db.commit()
        for row in to_insert:
            await db.refresh(row)

    return AuditIngestResult(
        accepted=len(to_insert),
        skipped=skipped,
        duplicates=duplicates,
        ids=[str(row.id) for row in to_insert],
    )


async def ingest_audit_events_sync(
    db: AsyncSession,
    tenant_id: UUID,
    raw_events: list[dict],
) -> AuditIngestResult:
    if len(raw_events) > MAX_SYNC_BATCH:
        raise ValueError(f"Sync ingest supports at most {MAX_SYNC_BATCH} events — use async batch endpoint")
    return await ingest_audit_events(db, tenant_id, raw_events)


async def audit_ingest_stats(db: AsyncSession, tenant_id: UUID, days: int = 7) -> list[dict]:
    from datetime import timedelta

    since = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(AuditLog.source, func.count(AuditLog.id))
        .where(AuditLog.tenant_id == tenant_id, AuditLog.timestamp >= since)
        .group_by(AuditLog.source)
        .order_by(func.count(AuditLog.id).desc())
    )
    return [{"source": source, "count": count} for source, count in result.all()]
