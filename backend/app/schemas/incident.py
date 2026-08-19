"""Security incident event model and dispatch policy for ITSM connectors."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

IncidentSource = Literal["gateway", "mcp", "rag", "scanner", "audit", "browser_extension"]
DuplicateAction = Literal["update", "skip"]

DEFAULT_ALLOWED_SOURCES: list[str] = ["gateway", "mcp", "rag", "scanner", "audit", "browser_extension"]


class IncidentDispatchPolicy(BaseModel):
    enabled: bool = True
    min_risk: str = "high"
    allowed_sources: list[str] = Field(default_factory=lambda: list(DEFAULT_ALLOWED_SOURCES))
    dedup_window_minutes: int = 15
    on_duplicate: DuplicateAction = "update"


class SecurityIncidentEvent(BaseModel):
    event_id: str
    trace_id: str | None = None
    tenant_id: str
    tenant_slug: str | None = None
    source: IncidentSource
    action: str
    title: str
    actor: str
    resource: str
    status: str
    risk: str
    policy_bundle: str | None = None
    matched_rule: str | None = None
    details: str = ""
    occurred_at: str
    fingerprint: str | None = None

    def with_fingerprint(self) -> SecurityIncidentEvent:
        if self.fingerprint:
            return self
        fp = compute_incident_fingerprint(self)
        return self.model_copy(update={"fingerprint": fp})


def compute_incident_fingerprint(event: SecurityIncidentEvent) -> str:
    """Stable SHA-256 hex from tenant, source, action, policy, rule, actor."""
    parts = [
        event.tenant_id,
        event.source,
        event.action,
        event.policy_bundle or "",
        event.matched_rule or "",
        _normalize_actor(event.actor),
    ]
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_actor(actor: str) -> str:
    actor = (actor or "").strip().lower()
    if "@" in actor:
        local, domain = actor.split("@", 1)
        return f"{local}@{domain}"
    return actor


RISK_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def risk_meets_minimum(risk: str, min_risk: str) -> bool:
    return RISK_ORDER.get((risk or "").lower(), 0) >= RISK_ORDER.get((min_risk or "high").lower(), 2)


def parse_dispatch_policy(raw: dict[str, Any] | None) -> IncidentDispatchPolicy:
    if not raw:
        return IncidentDispatchPolicy()
    return IncidentDispatchPolicy.model_validate(raw)


def policy_allows_event(policy: IncidentDispatchPolicy, event: SecurityIncidentEvent) -> bool:
    if not policy.enabled:
        return False
    if not risk_meets_minimum(event.risk, policy.min_risk):
        return False
    allowed = {s.lower() for s in policy.allowed_sources}
    return event.source.lower() in allowed


class AdapterResult(BaseModel):
    external_ticket_id: str
    external_url: str | None = None
    raw_response: dict[str, Any] | None = None


def incident_event_to_alert_dict(event: SecurityIncidentEvent) -> dict[str, Any]:
    """Convert to legacy alert webhook dict for Slack payloads."""
    data: dict[str, Any] = {
        "title": event.title,
        "action": event.action,
        "actor": event.actor,
        "resource": event.resource,
        "status": event.status,
        "risk": event.risk,
        "details": event.details,
    }
    if event.tenant_slug:
        data["tenant"] = event.tenant_slug
    if event.trace_id:
        data["trace_id"] = event.trace_id
    return data


def isoformat_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat().replace("+00:00", "Z")
