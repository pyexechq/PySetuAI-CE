"""Audit logging for MCP tool invocations (BL-098)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog
from app.services.gateway_context import GatewayContext
from app.core.telemetry import current_trace_id

logger = logging.getLogger(__name__)


def build_compliance_metadata(
    ctx: GatewayContext,
    *,
    server_id: uuid.UUID | None = None,
    tool_name: str | None = None,
    deny_reason: str | None = None,
    inspect_actions: list[str] | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "auth_type": "client_key" if ctx.client_api_key_id else "jwt",
        "client_api_key_id": str(ctx.client_api_key_id) if ctx.client_api_key_id else None,
        "policy_bundle_id": str(ctx.policy_bundle_id) if ctx.policy_bundle_id else None,
        "policy_bundle_name": ctx.policy_bundle_name,
    }
    if server_id:
        meta["mcp_server_id"] = str(server_id)
    if tool_name:
        meta["tool_name"] = tool_name
    if deny_reason:
        meta["deny_reason"] = deny_reason
    if inspect_actions:
        meta["inspect_actions"] = inspect_actions
    return meta


async def log_mcp_tool_invoke(
    db: AsyncSession,
    ctx: GatewayContext,
    *,
    server_name: str,
    server_id: uuid.UUID,
    tool_name: str,
    status: str,
    risk: str,
    details: str,
    latency_ms: int = 0,
    compliance_metadata: dict[str, Any] | None = None,
) -> uuid.UUID:
    trace_id = current_trace_id()
    audit_details = details
    if latency_ms:
        audit_details = f"latency_ms={latency_ms}; {audit_details}"
    if trace_id:
        audit_details = f"trace_id={trace_id}; {audit_details}"
    if ctx.policy_bundle_name:
        audit_details = f"bundle={ctx.policy_bundle_name}; {audit_details}"
    if ctx.client_api_key_name:
        audit_details = f"client_key={ctx.client_api_key_name}; {audit_details}"

    compliance = compliance_metadata or build_compliance_metadata(
        ctx, server_id=server_id, tool_name=tool_name
    )
    log = AuditLog(
        tenant_id=ctx.tenant_id,
        timestamp=datetime.now(UTC),
        actor=ctx.actor,
        action="MCP Tool Invoke",
        resource=f"{server_name}/{tool_name}",
        status=status,
        risk=risk,
        details=audit_details,
        usage_metadata={"compliance_metadata": compliance},
    )
    db.add(log)
    await db.flush()

    if status == "blocked":
        try:
            from app.services.incident_dispatch_service import dispatch_security_incident_from_audit

            refreshed = await db.get(AuditLog, log.id)
            if refreshed:
                await dispatch_security_incident_from_audit(db, refreshed)
        except Exception as exc:
            logger.warning("MCP incident dispatch failed: %s", exc)

    return log.id
