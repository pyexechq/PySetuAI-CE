"""Audit logging for governed RAG gateway operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog


async def write_rag_audit(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    actor: str,
    action: str,
    resource: str,
    status: str,
    risk: str,
    details: str,
    usage_metadata: dict[str, Any] | None = None,
) -> uuid.UUID:
    metadata = dict(usage_metadata or {})
    metadata.setdefault("module", "rag_gateway")
    log_id = uuid.uuid4()
    log = AuditLog(
        id=log_id,
        tenant_id=tenant_id,
        timestamp=datetime.now(UTC),
        actor=actor,
        action=action,
        resource=resource,
        status=status,
        risk=risk,
        details=details,
        usage_metadata=metadata,
        source="internal",
    )
    db.add(log)
    await db.flush()

    if status == "blocked":
        try:
            from app.services.incident_dispatch_service import dispatch_security_incident_from_audit

            refreshed = await db.get(AuditLog, log_id)
            if refreshed:
                await dispatch_security_incident_from_audit(db, refreshed)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("RAG incident dispatch failed: %s", exc)

    return log_id
