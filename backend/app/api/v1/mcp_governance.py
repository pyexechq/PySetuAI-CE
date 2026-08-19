"""MCP governance depth API — per-tool policies and tool-chain monitoring (Phase 3)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import MANAGE_AGENTS, MANAGE_MCP, VIEW_AGENTS, VIEW_AUDIT_LOGS, require_any_permission
from app.db.session import get_db
from app.models.governance import MCPServer, MCPToolPolicy
from app.models.tenant import User
from app.schemas.mcp_governance import (
    MCPToolChainEventResponse,
    MCPToolChainGraphResponse,
    MCPToolChainSummaryResponse,
    MCPToolPolicyResponse,
    MCPToolPolicyUpsertRequest,
)
from app.services.mcp_tool_chain_service import (
    chain_event_to_dict,
    chain_graph,
    chain_summary,
    list_chain_events,
)
from app.services.mcp_tool_policy_service import (
    delete_tool_policy,
    list_tool_policies,
    policy_to_dict,
    upsert_tool_policy,
)

router = APIRouter()

_require_mcp_admin = require_any_permission(MANAGE_MCP, MANAGE_AGENTS)
_require_chain_view = require_any_permission(VIEW_AUDIT_LOGS, VIEW_AGENTS, MANAGE_MCP)


async def _server(db: AsyncSession, tenant_id: uuid.UUID, server_id: uuid.UUID) -> MCPServer:
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id, MCPServer.tenant_id == tenant_id))
    server = result.scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found")
    return server


@router.get("/mcp/tool-policies", response_model=list[MCPToolPolicyResponse])
async def get_tool_policies(
    current_user: Annotated[User, Depends(_require_mcp_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MCPToolPolicy]:
    return await list_tool_policies(db, current_user.tenant_id)


@router.put("/mcp/tool-policies", response_model=MCPToolPolicyResponse)
async def put_tool_policy(
    payload: MCPToolPolicyUpsertRequest,
    current_user: Annotated[User, Depends(_require_mcp_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MCPToolPolicy:
    await _server(db, current_user.tenant_id, payload.server_id)
    try:
        policy = await upsert_tool_policy(
            db,
            current_user.tenant_id,
            server_id=payload.server_id,
            tool_name=payload.tool_name,
            action=payload.action,
            risk_score=payload.risk_score,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    await db.commit()
    return policy


@router.delete("/mcp/tool-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def remove_tool_policy(
    policy_id: uuid.UUID,
    current_user: Annotated[User, Depends(_require_mcp_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    deleted = await delete_tool_policy(db, current_user.tenant_id, policy_id)
    await db.commit()
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool policy not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/mcp/tool-chains", response_model=list[MCPToolChainEventResponse])
async def get_tool_chains(
    current_user: Annotated[User, Depends(_require_chain_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=200, ge=1, le=1000),
    decision: str | None = Query(default=None),
) -> list[dict]:
    events = await list_chain_events(db, current_user.tenant_id, limit=limit, decision=decision)
    return [chain_event_to_dict(event) for event in events]


@router.get("/mcp/tool-chains/summary", response_model=MCPToolChainSummaryResponse)
async def get_tool_chain_summary(
    current_user: Annotated[User, Depends(_require_chain_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await chain_summary(db, current_user.tenant_id)


@router.get("/mcp/tool-chains/graph", response_model=MCPToolChainGraphResponse)
async def get_tool_chain_graph(
    current_user: Annotated[User, Depends(_require_chain_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict:
    return await chain_graph(db, current_user.tenant_id, limit=limit)
