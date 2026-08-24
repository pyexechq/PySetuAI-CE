"""MCP tool-chain risk scoring, event monitoring, and attack-surface graph (Phase 3)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agentic import AgentInventory, MCPToolChainEvent
from app.services.agentic_service import SENSITIVE_DATA_KEYWORDS, risk_band

# Base risk contribution per tool risk class (0-100 scale).
TOOL_RISK_BASE: dict[str, int] = {
    "read": 10,
    "write": 30,
    "destructive": 50,
}

# External services that are considered trusted (no risk contribution).
TRUSTED_EXTERNAL_SERVICES: set[str] = {
    "github",
    "gitlab",
    "jira",
    "confluence",
    "slack",
    "teams",
    "salesforce",
    "servicenow",
    "datadog",
    "splunk",
    "pagerduty",
    "aws",
    "azure",
    "gcp",
}


def compute_chain_risk_score(
    tool_risk: str,
    data_source: str = "",
    external_service: str = "",
    agent_risk: int = 0,
    mcp_server_risk: float = 0.0,
) -> int:
    """Deterministic 0-100 chain risk score.

    Base from tool risk class plus bounded contributions from sensitive data
    sources, external services, agent risk, and MCP server risk. Reuses the
    agentic control-plane risk conventions for consistency.
    """
    score = TOOL_RISK_BASE.get(tool_risk, 10)

    lowered_source = (data_source or "").lower()
    for keyword, weight in SENSITIVE_DATA_KEYWORDS.items():
        if keyword in lowered_source:
            score += weight
            break

    lowered_ext = (external_service or "").lower()
    if lowered_ext and not any(vendor in lowered_ext for vendor in TRUSTED_EXTERNAL_SERVICES):
        score += 15

    score += max(0, min(15, agent_risk // 7))
    score += max(0, min(10, int(mcp_server_risk)))

    return max(0, min(100, score))


async def resolve_source_agent(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    actor: str,
) -> uuid.UUID | None:
    """Resolve the source agent id from a gateway actor string.

    The gateway actor is either ``client-key:{name}`` or a user email. We match
    the client-key name (and fall back to the raw actor) against the agent
    inventory so chain events carry agent-to-agent attribution when available.
    """
    if not actor:
        return None
    candidate = actor
    if actor.startswith("client-key:"):
        candidate = actor[len("client-key:") :]
    result = await db.execute(
        select(AgentInventory.id)
        .where(AgentInventory.tenant_id == tenant_id, AgentInventory.name == candidate)
        .limit(1)
    )
    agent_id = result.scalar_one_or_none()
    if agent_id is not None:
        return agent_id
    result = await db.execute(
        select(AgentInventory.id)
        .where(AgentInventory.tenant_id == tenant_id, AgentInventory.name == actor)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def record_mcp_chain_event(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    security_event_id: uuid.UUID | None = None,
    approval_request_id: uuid.UUID | None = None,
    source_agent_id: uuid.UUID | None = None,
    target_agent_id: uuid.UUID | None = None,
    endpoint_id: uuid.UUID | None = None,
    mcp_server_id: uuid.UUID | None = None,
    mcp_server_name: str = "",
    tool_name: str = "",
    tool_risk: str = "read",
    data_source: str = "",
    external_service: str = "",
    decision: str,
    chain_risk_score: int = 0,
    policy_id: str | None = None,
    policy_name: str = "",
    metadata: dict[str, Any] | None = None,
) -> MCPToolChainEvent:
    event = MCPToolChainEvent(
        tenant_id=tenant_id,
        security_event_id=security_event_id,
        approval_request_id=approval_request_id,
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        endpoint_id=endpoint_id,
        mcp_server_id=mcp_server_id,
        mcp_server_name=mcp_server_name,
        tool_name=tool_name,
        tool_risk=tool_risk,
        data_source=data_source,
        external_service=external_service,
        decision=decision,
        chain_risk_score=chain_risk_score,
        policy_id=policy_id,
        policy_name=policy_name,
        metadata_json=metadata,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def list_chain_events(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    limit: int = 200,
    decision: str | None = None,
) -> list[MCPToolChainEvent]:
    stmt = select(MCPToolChainEvent).where(MCPToolChainEvent.tenant_id == tenant_id)
    if decision and decision != "all":
        stmt = stmt.where(MCPToolChainEvent.decision == decision)
    stmt = stmt.order_by(MCPToolChainEvent.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def chain_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    total = int(
        await db.scalar(
            select(func.count(MCPToolChainEvent.id)).where(MCPToolChainEvent.tenant_id == tenant_id)
        )
        or 0
    )
    decision_rows = (
        await db.execute(
            select(MCPToolChainEvent.decision, func.count(MCPToolChainEvent.id))
            .where(MCPToolChainEvent.tenant_id == tenant_id)
            .group_by(MCPToolChainEvent.decision)
        )
    ).all()
    risk_rows = (
        await db.execute(
            select(MCPToolChainEvent.tool_risk, func.count(MCPToolChainEvent.id))
            .where(MCPToolChainEvent.tenant_id == tenant_id)
            .group_by(MCPToolChainEvent.tool_risk)
        )
    ).all()
    ext_rows = (
        await db.execute(
            select(MCPToolChainEvent.external_service, func.count(MCPToolChainEvent.id))
            .where(
                MCPToolChainEvent.tenant_id == tenant_id,
                MCPToolChainEvent.external_service != "",
            )
            .group_by(MCPToolChainEvent.external_service)
        )
    ).all()
    by_decision = {decision: int(count) for decision, count in decision_rows}
    by_tool_risk = {risk: int(count) for risk, count in risk_rows}
    by_external_service = {ext: int(count) for ext, count in ext_rows}
    high_risk = int(
        await db.scalar(
            select(func.count(MCPToolChainEvent.id)).where(
                MCPToolChainEvent.tenant_id == tenant_id,
                MCPToolChainEvent.chain_risk_score >= 60,
            )
        )
        or 0
    )
    return {
        "total": total,
        "allowed": by_decision.get("allowed", 0),
        "blocked": by_decision.get("blocked", 0),
        "approval": by_decision.get("approval", 0),
        "high_risk": high_risk,
        "by_decision": by_decision,
        "by_tool_risk": by_tool_risk,
        "by_external_service": by_external_service,
    }


_NODE_COLORS: dict[str, str] = {
    "agent": "#3b82f6",
    "mcp_server": "#f97316",
    "tool": "#a855f7",
    "data_source": "#22c55e",
    "external_service": "#ef4444",
}


def _node_id(node_type: str, label: str) -> str:
    return f"{node_type}:{label}"


async def chain_graph(db: AsyncSession, tenant_id: uuid.UUID, *, limit: int = 200) -> dict[str, Any]:
    events = await list_chain_events(db, tenant_id, limit=limit)
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def add_node(node_type: str, label: str, risk_score: int) -> None:
        if not label:
            return
        nid = _node_id(node_type, label)
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "label": label,
                "type": node_type,
                "risk_score": risk_score,
                "color": _NODE_COLORS.get(node_type, "#94a3b8"),
            }
        else:
            nodes[nid]["risk_score"] = max(nodes[nid]["risk_score"], risk_score)

    def add_edge(frm: str, to: str, label: str, risk_score: int) -> None:
        if not frm or not to:
            return
        edges.append({"from": frm, "to": to, "label": label, "risk_score": risk_score})

    for event in events:
        risk = event.chain_risk_score
        source_id_str = str(event.source_agent_id)[:8] if event.source_agent_id else "unknown"
        target_id_str = str(event.target_agent_id)[:8] if event.target_agent_id else "unknown"
        
        source_label = f"Agent ({source_id_str})"
        target_label = f"Agent ({target_id_str})"
        server_label = event.mcp_server_name or "mcp:unknown"
        tool_label = event.tool_name or "tool:unknown"
        data_label = event.data_source or "data:unknown"
        ext_label = event.external_service or "external:unknown"

        add_node("agent", source_label, risk)
        add_node("agent", target_label, risk)
        add_node("mcp_server", server_label, risk)
        add_node("tool", tool_label, risk)
        add_node("data_source", data_label, risk)
        add_node("external_service", ext_label, risk)

        add_edge(_node_id("agent", source_label), _node_id("agent", target_label), "calls", risk)
        add_edge(_node_id("agent", target_label), _node_id("mcp_server", server_label), "uses", risk)
        add_edge(_node_id("mcp_server", server_label), _node_id("tool", tool_label), "invokes", risk)
        add_edge(_node_id("tool", tool_label), _node_id("data_source", data_label), "reads", risk)
        add_edge(_node_id("tool", tool_label), _node_id("external_service", ext_label), "calls", risk)

    return {"nodes": list(nodes.values()), "edges": edges}


def chain_event_to_dict(event: MCPToolChainEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "tenant_id": str(event.tenant_id),
        "security_event_id": str(event.security_event_id) if event.security_event_id else None,
        "approval_request_id": str(event.approval_request_id) if event.approval_request_id else None,
        "source_agent_id": str(event.source_agent_id) if event.source_agent_id else None,
        "target_agent_id": str(event.target_agent_id) if event.target_agent_id else None,
        "endpoint_id": str(event.endpoint_id) if event.endpoint_id else None,
        "mcp_server_id": str(event.mcp_server_id) if event.mcp_server_id else None,
        "mcp_server_name": event.mcp_server_name,
        "tool_name": event.tool_name,
        "tool_risk": event.tool_risk,
        "data_source": event.data_source,
        "external_service": event.external_service,
        "decision": event.decision,
        "chain_risk_score": event.chain_risk_score,
        "risk_band": risk_band(event.chain_risk_score),
        "policy_id": event.policy_id,
        "policy_name": event.policy_name,
        "metadata_json": event.metadata_json,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
