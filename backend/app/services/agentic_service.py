"""Endpoint registration, agent inventory, and unified security-event services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agentic import AgentInventory, ApprovalRequest, Endpoint, SecurityEvent
from app.models.governance import AuditLog, PolicyBundle
from app.schemas.agentic import (
    AgentRegisterRequest,
    EndpointRegisterRequest,
    SecurityEventIngestRequest,
)

# Base risk contribution per agent type (0-100 scale).
AGENT_TYPE_BASE_RISK: dict[str, int] = {
    "coding_agent": 30,
    "ide_copilot": 25,
    "enterprise_copilot": 30,
    "teams_agent": 35,
    "copilot_studio_agent": 35,
    "autonomous_agent": 55,
    "mcp_agent": 40,
    "rag_agent": 20,
    "custom_agent": 30,
    "local_llm_agent": 15,
}

# Risk keywords matched against tool names.
TOOL_RISK_KEYWORDS: dict[str, int] = {
    "delete": 25,
    "remove": 20,
    "exec": 25,
    "shell": 25,
    "write": 15,
    "push": 15,
    "deploy": 20,
    "apply": 15,
    "destroy": 30,
    "admin": 20,
}

SENSITIVE_DATA_KEYWORDS: dict[str, int] = {
    "ssh": 20,
    "aws": 15,
    "credentials": 25,
    "secret": 25,
    ".env": 25,
    "pii": 20,
    "phi": 25,
    "pci": 25,
    "customer": 20,
    "production": 20,
}

RISK_BAND_LABELS: list[tuple[int, int, str]] = [
    (80, 100, "critical"),
    (60, 79, "high"),
    (30, 59, "medium"),
    (0, 29, "low"),
]

DEFAULT_FILE_GOVERNANCE_RULES: list[dict[str, str]] = [
    {"pattern": ".env", "classification": "*", "action": "block"},
    {"pattern": ".env.*", "classification": "*", "action": "block"},
    {"pattern": "*.pem", "classification": "*", "action": "block"},
    {"pattern": "*.key", "classification": "*", "action": "block"},
    {"pattern": "credentials.*", "classification": "*", "action": "block"},
    {"pattern": "~/.ssh/**", "classification": "*", "action": "block"},
    {"pattern": "~/.aws/**", "classification": "*", "action": "block"},
    {"pattern": "*.sql", "classification": "PII", "action": "redact"},
    {"pattern": "src/**", "classification": "*", "action": "allow"},
    {"pattern": "tests/**", "classification": "*", "action": "allow"},
]


def file_governance_rules_for_bundle(bundle: PolicyBundle | None) -> list[dict[str, str]]:
    if bundle is None:
        return DEFAULT_FILE_GOVERNANCE_RULES
    rules = bundle.file_governance_rules
    if not isinstance(rules, list) or len(rules) == 0:
        return DEFAULT_FILE_GOVERNANCE_RULES
    return [
        {
            "pattern": str(rule.get("pattern", "")),
            "classification": str(rule.get("classification", "*")),
            "action": str(rule.get("action", "allow")),
        }
        for rule in rules
        if isinstance(rule, dict) and rule.get("pattern")
    ] or DEFAULT_FILE_GOVERNANCE_RULES


def risk_band(score: int) -> str:
    for low, high, label in RISK_BAND_LABELS:
        if low <= score <= high:
            return label
    return "low"


def compute_agent_risk_score(
    agent_type: str,
    tools: list[str] | None = None,
    mcp_servers: list[str] | None = None,
    data_sources: list[str] | None = None,
    permissions: list[str] | None = None,
) -> int:
    """Deterministic 0-100 risk score from agent attributes.

    The formula intentionally favors explainability over machine learning: a base
    score by agent type plus bounded contributions from risky tools, MCP reach,
    sensitive data sources, and broad permissions.
    """
    score = AGENT_TYPE_BASE_RISK.get(agent_type, 30)

    for tool in tools or []:
        lowered = tool.lower()
        for keyword, weight in TOOL_RISK_KEYWORDS.items():
            if keyword in lowered:
                score += weight
                break

    if mcp_servers:
        score += min(15, 5 * len(mcp_servers))

    for source in data_sources or []:
        lowered = source.lower()
        for keyword, weight in SENSITIVE_DATA_KEYWORDS.items():
            if keyword in lowered:
                score += weight
                break

    broad_permissions = {p.lower() for p in permissions or []}
    if broad_permissions & {"admin", "root", "sudo", "write", "delete", "all"}:
        score += 15

    return max(0, min(100, score))


async def register_endpoint(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    payload: EndpointRegisterRequest,
) -> Endpoint:
    """Idempotently register an endpoint per (tenant_id, hostname)."""
    result = await db.execute(
        select(Endpoint).where(
            Endpoint.tenant_id == tenant_id,
            Endpoint.hostname == payload.hostname,
        )
    )
    endpoint = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if endpoint is None:
        endpoint = Endpoint(
            tenant_id=tenant_id,
            hostname=payload.hostname,
            os_name=payload.os_name,
            os_version=payload.os_version,
            agent_version=payload.agent_version,
            status="online",
            last_seen_at=now,
            metadata_json=payload.metadata,
        )
        db.add(endpoint)
    else:
        endpoint.os_name = payload.os_name or endpoint.os_name
        endpoint.os_version = payload.os_version or endpoint.os_version
        endpoint.agent_version = payload.agent_version or endpoint.agent_version
        endpoint.status = "online"
        endpoint.last_seen_at = now
        if payload.metadata:
            endpoint.metadata_json = payload.metadata
    await db.flush()
    await db.refresh(endpoint)
    return endpoint


async def heartbeat_endpoint(
    db: AsyncSession,
    endpoint: Endpoint,
    status: str,
    agent_version: str | None,
) -> Endpoint:
    endpoint.status = status
    endpoint.last_seen_at = datetime.now(UTC)
    if agent_version:
        endpoint.agent_version = agent_version
    await db.flush()
    return endpoint


async def upsert_agent(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    payload: AgentRegisterRequest,
) -> AgentInventory:
    endpoint_id = uuid.UUID(payload.endpoint_id) if payload.endpoint_id else None
    result = await db.execute(
        select(AgentInventory).where(
            AgentInventory.tenant_id == tenant_id,
            AgentInventory.endpoint_id == endpoint_id,
            AgentInventory.name == payload.name,
        )
    )
    agent = result.scalar_one_or_none()
    risk_score = compute_agent_risk_score(
        payload.agent_type,
        payload.tools,
        payload.mcp_servers,
        payload.data_sources,
        payload.permissions,
    )
    if agent is None:
        agent = AgentInventory(
            tenant_id=tenant_id,
            endpoint_id=endpoint_id,
            name=payload.name,
            agent_type=payload.agent_type,
            vendor=payload.vendor,
            version=payload.version,
            user_name=payload.user_name,
            status=payload.status,
            risk_score=risk_score,
            data_sources=payload.data_sources,
            tools=payload.tools,
            mcp_servers=payload.mcp_servers,
            permissions=payload.permissions,
            last_activity_at=datetime.now(UTC),
        )
        db.add(agent)
    else:
        agent.agent_type = payload.agent_type
        agent.vendor = payload.vendor
        agent.version = payload.version
        agent.user_name = payload.user_name
        agent.status = payload.status
        agent.risk_score = risk_score
        agent.data_sources = payload.data_sources
        agent.tools = payload.tools
        agent.mcp_servers = payload.mcp_servers
        agent.permissions = payload.permissions
        agent.last_activity_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(agent)
    return agent


def _audit_status(decision: str) -> str:
    if decision == "allowed":
        return "allowed"
    if decision in {"blocked", "redacted", "approval"}:
        return decision
    return "logged"


async def record_security_event(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    payload: SecurityEventIngestRequest,
    *,
    actor: str,
) -> tuple[SecurityEvent, AuditLog]:
    """Persist a normalized security event and a linked AuditLog row.

    Returns both records so the caller can commit once. Raw content is intentionally
    not accepted here; callers transmit classifications, paths, and metadata only.
    """
    endpoint_id = uuid.UUID(payload.endpoint_id) if payload.endpoint_id else None
    agent_id = uuid.UUID(payload.agent_id) if payload.agent_id else None
    now = datetime.now(UTC)
    band = risk_band(payload.risk_score)

    audit = AuditLog(
        tenant_id=tenant_id,
        timestamp=now,
        actor=actor or payload.user_name,
        action=f"endpoint.{payload.action}"[:100],
        resource=payload.resource or "-",
        status=_audit_status(payload.decision),
        risk=band,
        details=(
            f"source={payload.source}; event_type={payload.event_type}; "
            f"tool={payload.tool or 'unknown'}; "
            f"classification={', '.join(payload.classification) or 'none'}"
        )[:4000],
        usage_metadata={
            "source": payload.source,
            "event_type": payload.event_type,
            "tool": payload.tool,
            "classification": payload.classification,
            "policy_id": payload.policy_id,
            "policy_name": payload.policy_name,
        },
        source=payload.source or "endpoint",
    )
    db.add(audit)
    await db.flush()

    event = SecurityEvent(
        tenant_id=tenant_id,
        endpoint_id=endpoint_id,
        agent_id=agent_id,
        audit_log_id=audit.id,
        source=payload.source,
        event_type=payload.event_type,
        user_name=payload.user_name,
        tool=payload.tool,
        action=payload.action,
        resource=payload.resource,
        classification=payload.classification,
        decision=payload.decision,
        risk_score=payload.risk_score,
        policy_id=payload.policy_id,
        policy_name=payload.policy_name,
        metadata_json=payload.metadata,
    )
    db.add(event)
    await db.flush()

    if payload.decision == "approval":
        db.add(
            ApprovalRequest(
                tenant_id=tenant_id,
                security_event_id=event.id,
                endpoint_id=endpoint_id,
                agent_id=agent_id,
                user_name=payload.user_name,
                tool=payload.tool,
                action=payload.action,
                resource=payload.resource,
                classification=payload.classification,
                risk_score=payload.risk_score,
                policy_id=payload.policy_id,
                policy_name=payload.policy_name,
                status="pending",
                expires_at=now + timedelta(hours=24),
            )
        )
        await db.flush()

    return event, audit


async def security_event_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    total = await db.scalar(
        select(func.count(SecurityEvent.id)).where(SecurityEvent.tenant_id == tenant_id)
    )
    decision_rows = (
        await db.execute(
            select(SecurityEvent.decision, func.count(SecurityEvent.id))
            .where(SecurityEvent.tenant_id == tenant_id)
            .group_by(SecurityEvent.decision)
        )
    ).all()
    type_rows = (
        await db.execute(
            select(SecurityEvent.event_type, func.count(SecurityEvent.id))
            .where(SecurityEvent.tenant_id == tenant_id)
            .group_by(SecurityEvent.event_type)
        )
    ).all()
    by_decision = {decision: int(count) for decision, count in decision_rows}
    by_type = {event_type: int(count) for event_type, count in type_rows}
    high_risk = int(
        await db.scalar(
            select(func.count(SecurityEvent.id)).where(
                SecurityEvent.tenant_id == tenant_id,
                SecurityEvent.risk_score >= 60,
            )
        )
        or 0
    )
    return {
        "total": int(total or 0),
        "blocked": by_decision.get("blocked", 0),
        "redacted": by_decision.get("redacted", 0),
        "allowed": by_decision.get("allowed", 0),
        "high_risk": high_risk,
        "by_decision": by_decision,
        "by_type": by_type,
    }


async def list_approvals(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    status_filter: str | None = None,
) -> list[ApprovalRequest]:
    stmt = select(ApprovalRequest).where(ApprovalRequest.tenant_id == tenant_id)
    if status_filter and status_filter != "all":
        stmt = stmt.where(ApprovalRequest.status == status_filter)
    stmt = stmt.order_by(ApprovalRequest.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def decide_approval(
    db: AsyncSession,
    approval: ApprovalRequest,
    decision: str,
    decided_by: str,
    reason: str = "",
) -> ApprovalRequest:
    approval.status = decision
    approval.decided_by = decided_by
    approval.decided_at = datetime.now(UTC)
    if reason:
        approval.reason = reason
    await db.flush()
    return approval
