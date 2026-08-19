"""Per-tool MCP governance policies — allow / approval / block (Phase 3)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import MCPToolPolicy

ALLOWED_ACTIONS = {"allow", "approval", "block"}


async def list_tool_policies(db: AsyncSession, tenant_id: uuid.UUID) -> list[MCPToolPolicy]:
    result = await db.execute(
        select(MCPToolPolicy)
        .where(MCPToolPolicy.tenant_id == tenant_id)
        .order_by(MCPToolPolicy.server_id, MCPToolPolicy.tool_name)
    )
    return list(result.scalars().all())


async def upsert_tool_policy(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    server_id: uuid.UUID,
    tool_name: str,
    action: str,
    risk_score: int = 0,
    reason: str = "",
) -> MCPToolPolicy:
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"action must be one of: {', '.join(sorted(ALLOWED_ACTIONS))}")
    result = await db.execute(
        select(MCPToolPolicy).where(
            MCPToolPolicy.tenant_id == tenant_id,
            MCPToolPolicy.server_id == server_id,
            MCPToolPolicy.tool_name == tool_name,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        policy = MCPToolPolicy(
            tenant_id=tenant_id,
            server_id=server_id,
            tool_name=tool_name,
            action=action,
            risk_score=risk_score,
            reason=reason,
        )
        db.add(policy)
    else:
        policy.action = action
        policy.risk_score = risk_score
        policy.reason = reason
    await db.flush()
    await db.refresh(policy)
    return policy


async def delete_tool_policy(db: AsyncSession, tenant_id: uuid.UUID, policy_id: uuid.UUID) -> bool:
    result = await db.execute(
        delete(MCPToolPolicy).where(
            MCPToolPolicy.tenant_id == tenant_id,
            MCPToolPolicy.id == policy_id,
        )
    )
    await db.flush()
    return bool(result.rowcount)


async def resolve_tool_action(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    server_id: uuid.UUID,
    tool_name: str,
) -> tuple[str, MCPToolPolicy | None]:
    """Return the governance action for a tool: allow | approval | block.

    Defaults to ``allow`` when no policy exists so existing behavior is unchanged.
    """
    result = await db.execute(
        select(MCPToolPolicy).where(
            MCPToolPolicy.tenant_id == tenant_id,
            MCPToolPolicy.server_id == server_id,
            MCPToolPolicy.tool_name == tool_name,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        return "allow", None
    return policy.action, policy


async def policies_for_server(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    server_id: uuid.UUID,
) -> dict[str, MCPToolPolicy]:
    result = await db.execute(
        select(MCPToolPolicy).where(
            MCPToolPolicy.tenant_id == tenant_id,
            MCPToolPolicy.server_id == server_id,
        )
    )
    return {policy.tool_name: policy for policy in result.scalars().all()}


def policy_to_dict(policy: MCPToolPolicy) -> dict[str, Any]:
    return {
        "id": str(policy.id),
        "tenant_id": str(policy.tenant_id),
        "server_id": str(policy.server_id),
        "tool_name": policy.tool_name,
        "action": policy.action,
        "risk_score": policy.risk_score,
        "reason": policy.reason,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }
