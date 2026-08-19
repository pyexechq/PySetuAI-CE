"""Build SecurityIncidentEvent from audit logs and gateway alert dicts."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.models.governance import AuditLog
from app.schemas.incident import SecurityIncidentEvent, isoformat_dt
from app.schemas.security import SecurityScanResponse

_TRACE_RE = re.compile(r"trace_id=([^;\s]+)")
_BUNDLE_RE = re.compile(r"bundle=([^;]+)")


def map_audit_source(audit_log: AuditLog) -> str:
    meta = audit_log.usage_metadata or {}
    if isinstance(meta.get("compliance_metadata"), dict):
        meta = {**meta, **meta["compliance_metadata"]}
    if meta.get("module") == "rag_gateway":
        return "rag"
    action = (audit_log.action or "").strip()
    if action == "MCP Tool Invoke":
        return "mcp"
    if action.startswith("RAG"):
        return "rag"
    if meta.get("source") == "scanner":
        return "scanner"
    if action in {"Policy Inspection", "ABAC Policy", "LLM Request", "LLM Response"}:
        return "gateway"
    return "audit"


def map_audit_action(audit_log: AuditLog) -> str:
    action = (audit_log.action or "").strip()
    status = (audit_log.status or "").strip().lower()
    source = map_audit_source(audit_log)

    if source == "mcp" and status == "blocked":
        return "mcp.tool.block"
    if source == "rag" and status == "blocked":
        return "rag.movement.block"
    if source == "gateway" and status == "blocked":
        if action == "ABAC Policy":
            return "gateway.abac.block"
        if action == "LLM Response":
            return "gateway.egress.block"
        if action == "Policy Inspection":
            return "gateway.prompt.block"
        return "gateway.policy.block"
    if source == "scanner":
        return "scanner.threat.detected"
    return action.lower().replace(" ", ".")


def _parse_trace_id(details: str) -> str | None:
    match = _TRACE_RE.search(details or "")
    return match.group(1) if match else None


def _parse_policy_bundle(details: str, usage_metadata: dict[str, Any] | None) -> str | None:
    meta = usage_metadata or {}
    if meta.get("policy_bundle_name"):
        return str(meta["policy_bundle_name"])
    compliance = meta.get("compliance_metadata") or {}
    if isinstance(compliance, dict) and compliance.get("policy_bundle_name"):
        return str(compliance["policy_bundle_name"])
    match = _BUNDLE_RE.search(details or "")
    return match.group(1).strip() if match else None


def _parse_matched_rule(usage_metadata: dict[str, Any] | None) -> str | None:
    meta = usage_metadata or {}
    if meta.get("matched_rule"):
        return str(meta["matched_rule"])
    if meta.get("rule_id"):
        return str(meta["rule_id"])
    matches = meta.get("matches")
    if isinstance(matches, list) and matches:
        first = matches[0]
        if isinstance(first, dict) and first.get("rule_id"):
            return str(first["rule_id"])
    return None


def _title_for_event(source: str, action: str, resource: str) -> str:
    titles = {
        "gateway.policy.block": "Gateway request blocked by policy",
        "gateway.injection.block": "Prompt injection blocked",
        "gateway.abac.block": "Gateway request blocked by ABAC",
        "gateway.egress.block": "Gateway response blocked by egress policy",
        "gateway.prompt.block": "Ad-hoc system prompt blocked",
        "gateway.rate_limit.block": "AI rate limit exceeded",
        "gateway.token_budget.block": "AI token budget limit exceeded",
        "mcp.tool.block": "MCP tool invocation blocked",
        "rag.movement.block": "RAG data movement blocked",
        "scanner.threat.detected": "Security scanner threat detected",
    }
    if action in titles:
        return titles[action]
    if source == "rag":
        return f"RAG violation — {resource}"
    return f"Security incident — {action}"


def build_security_incident_event_from_audit(
    audit_log: AuditLog,
    *,
    tenant_slug: str | None = None,
) -> SecurityIncidentEvent:
    source = map_audit_source(audit_log)
    action = map_audit_action(audit_log)
    details = audit_log.details or ""
    meta = audit_log.usage_metadata or {}

    event = SecurityIncidentEvent(
        event_id=str(audit_log.id),
        trace_id=_parse_trace_id(details),
        tenant_id=str(audit_log.tenant_id),
        tenant_slug=tenant_slug,
        source=source,
        action=action,
        title=_title_for_event(source, action, audit_log.resource),
        actor=audit_log.actor,
        resource=audit_log.resource,
        status=audit_log.status,
        risk=audit_log.risk or "medium",
        policy_bundle=_parse_policy_bundle(details, meta),
        matched_rule=_parse_matched_rule(meta),
        details=details[:4000],
        occurred_at=isoformat_dt(audit_log.timestamp),
    )
    return event.with_fingerprint()


def security_incident_event_from_gateway_dict(
    tenant_id: uuid.UUID,
    event: dict[str, Any],
    *,
    tenant_slug: str | None = None,
    source: str = "gateway",
) -> SecurityIncidentEvent:
    action = str(event.get("action", "gateway.policy.block"))
    incident = SecurityIncidentEvent(
        event_id=str(uuid.uuid4()),
        trace_id=event.get("trace_id"),
        tenant_id=str(tenant_id),
        tenant_slug=tenant_slug or event.get("tenant"),
        source=source,
        action=action,
        title=str(event.get("title", "PySetu gateway alert")),
        actor=str(event.get("actor", "unknown")),
        resource=str(event.get("resource", "n/a")),
        status=str(event.get("status", "blocked")),
        risk=str(event.get("risk", "high")),
        policy_bundle=event.get("policy_bundle"),
        matched_rule=event.get("matched_rule"),
        details=str(event.get("details", ""))[:4000],
        occurred_at=event.get("occurred_at") or isoformat_dt(datetime.now(UTC)),
    )
    return incident.with_fingerprint()


def build_security_incident_event_from_scan(
    tenant_id: uuid.UUID,
    actor: str,
    content_preview: str,
    result: SecurityScanResponse,
    *,
    tenant_slug: str | None = None,
) -> SecurityIncidentEvent | None:
    if not result.detected:
        return None
    severity = (result.highest_severity or "medium").lower()
    if severity not in {"high", "critical"}:
        return None

    top_match = result.matches[0] if result.matches else None
    matched_rule = top_match.rule_id if top_match else None
    detail_parts = [f"action={result.recommended_action}"]
    if top_match:
        detail_parts.append(f"rule={top_match.name}: {top_match.detail}")
    detail_parts.append(f"preview={content_preview[:200]}")

    event = SecurityIncidentEvent(
        event_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        tenant_slug=tenant_slug,
        source="scanner",
        action="scanner.threat.detected",
        title="Security scanner threat detected",
        actor=actor,
        resource="security/scan",
        status="review",
        risk=severity,
        matched_rule=matched_rule,
        details="; ".join(detail_parts),
        occurred_at=isoformat_dt(datetime.now(UTC)),
        policy_bundle=None,
    )
    return event.with_fingerprint()
