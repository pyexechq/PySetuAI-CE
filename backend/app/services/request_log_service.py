"""Full request/response log retention and retrieval (BL-073)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLogBody
from app.models.tenant import Tenant
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse, InspectionResult

_MAX_JSON_CHARS = 65536
_DEFAULT_RETENTION_DAYS = 30


def _truncate_payload(value: Any) -> Any:
    if value is None:
        return None
    try:
        encoded = json.dumps(value, default=str)
    except TypeError:
        encoded = str(value)
    if len(encoded) <= _MAX_JSON_CHARS:
        return value
    return {
        "_truncated": True,
        "_original_chars": len(encoded),
        "preview": encoded[:_MAX_JSON_CHARS],
    }


def serialize_chat_request(request: ChatCompletionRequest | None) -> dict[str, Any] | None:
    if request is None:
        return None
    return _truncate_payload(request.model_dump(exclude_none=True))


def serialize_chat_response(response: ChatCompletionResponse | None) -> dict[str, Any] | None:
    if response is None:
        return None
    return _truncate_payload(response.model_dump(exclude_none=True))


def build_guardrail_events(
    ingress: InspectionResult | None = None,
    egress: InspectionResult | None = None,
) -> dict[str, Any] | None:
    payload: dict[str, Any] = {}
    if ingress is not None:
        payload["ingress"] = {
            "allowed": ingress.allowed,
            "action": ingress.action,
            "risk": ingress.risk,
            "violations": [v.model_dump() for v in ingress.violations],
            "redacted_content": ingress.redacted_content,
        }
    if egress is not None:
        payload["egress"] = {
            "allowed": egress.allowed,
            "action": egress.action,
            "risk": egress.risk,
            "violations": [v.model_dump() for v in egress.violations],
            "redacted_content": egress.redacted_content,
        }
    return payload or None


async def store_request_log_body(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    audit_log_id: uuid.UUID,
    request_payload: dict[str, Any] | None = None,
    response_payload: dict[str, Any] | None = None,
    guardrail_events: dict[str, Any] | None = None,
    tool_events: list[dict[str, Any]] | None = None,
) -> None:
    if not any([request_payload, response_payload, guardrail_events, tool_events]):
        return
    db.add(
        AuditLogBody(
            tenant_id=tenant_id,
            audit_log_id=audit_log_id,
            request_payload=request_payload,
            response_payload=response_payload,
            guardrail_events=guardrail_events,
            tool_events=tool_events,
        )
    )


async def get_request_log_body(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    audit_log_id: uuid.UUID,
) -> AuditLogBody | None:
    result = await db.execute(
        select(AuditLogBody).where(
            AuditLogBody.tenant_id == tenant_id,
            AuditLogBody.audit_log_id == audit_log_id,
        )
    )
    return result.scalar_one_or_none()


async def count_request_log_bodies(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count(AuditLogBody.id)).where(AuditLogBody.tenant_id == tenant_id)
    )
    return int(result.scalar_one() or 0)


async def purge_expired_request_logs(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    retention_days = tenant.request_log_retention_days if tenant else _DEFAULT_RETENTION_DAYS
    cutoff = datetime.now(UTC) - timedelta(days=max(1, retention_days))
    result = await db.execute(
        delete(AuditLogBody).where(
            AuditLogBody.tenant_id == tenant_id,
            AuditLogBody.created_at < cutoff,
        )
    )
    return int(result.rowcount or 0)


async def get_request_log_settings(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    retention_days = tenant.request_log_retention_days if tenant else _DEFAULT_RETENTION_DAYS
    stored = await count_request_log_bodies(db, tenant_id)
    return {
        "retention_days": retention_days,
        "stored_entries": stored,
    }


async def update_request_log_retention(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    retention_days: int,
) -> dict[str, Any]:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise ValueError("tenant not found")
    tenant.request_log_retention_days = max(1, min(365, retention_days))
    stored = await count_request_log_bodies(db, tenant_id)
    return {
        "retention_days": tenant.request_log_retention_days,
        "stored_entries": stored,
    }
