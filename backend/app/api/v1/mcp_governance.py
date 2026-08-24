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
    MCPPortalCatalogResponse,
    MCPPortalRequestStatusResponse,
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
_require_portal_view = require_any_permission(VIEW_AGENTS, MANAGE_MCP, MANAGE_AGENTS)


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


@router.get("/mcp/portal/catalog", response_model=MCPPortalCatalogResponse)
async def get_portal_catalog(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from app.models.tenant import Tenant
    tenant_res = await db.execute(select(Tenant).limit(1))
    tenant = tenant_res.scalar_one_or_none()
    
    # If portal is globally disabled for tenant, return empty servers list
    if tenant and tenant.mcp_portal_enabled is False:
        return {"servers": []}

    # Query published MCP servers from database
    result = await db.execute(select(MCPServer).order_by(MCPServer.name.asc()))
    servers = result.scalars().all()
    
    server_list = []
    for s in servers:
        # Respect per-server visibility toggle in portal
        if s.connection_config and s.connection_config.get("portal_visible") is False:
            continue

        tool_names = [str(n) for n in (s.tool_names or [])]
        features = ["Live MCP Protocol", f"{len(tool_names) or s.tools_count} Tools", "Policy-Governed"]
        if s.transport:
            features.append(f"{s.transport.upper()} Transport")
        
        server_list.append({
            "id": str(s.id),
            "name": s.name,
            "category": s.category or "Development",
            "status": "Available",
            "transport": s.transport or "sse",
            "endpoint_url": s.endpoint_url,
            "tools_count": s.tools_count or len(tool_names),
            "tool_names": tool_names,
            "description": f"Published MCP Server for {s.name} operations, providing {len(tool_names) or s.tools_count} secured tools.",
            "features": features,
            "requires_approval": True,
            "server_config": s.connection_config,
        })
    
    # Fallback only if no servers in DB
    if not server_list:
        server_list = [
            {
                "id": "mcp-fs-01",
                "name": "Local FileSystem MCP",
                "category": "Development",
                "status": "Available",
                "transport": "stdio",
                "endpoint_url": None,
                "tools_count": 3,
                "tool_names": ["read_file", "write_file", "list_directory"],
                "description": "Provides secure read/write access to specific local directories for your AI agents.",
                "features": ["Read-only mode", "Path restrictions", "MIME type filtering"],
                "requires_approval": False,
                "server_config": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]},
            },
            {
                "id": "mcp-gh-01",
                "name": "GitHub Integration MCP",
                "category": "Development",
                "status": "Available",
                "transport": "stdio",
                "endpoint_url": None,
                "tools_count": 3,
                "tool_names": ["search_repositories", "create_issue", "create_pull_request"],
                "description": "Interact with repositories, pull requests, issues, and git objects directly from AI models.",
                "features": ["Repo read/write", "Issue tracking", "PR automation"],
                "requires_approval": True,
                "server_config": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"]},
            },
            {
                "id": "mcp-pg-01",
                "name": "PostgreSQL Gateway MCP",
                "category": "Database",
                "status": "Available",
                "transport": "stdio",
                "endpoint_url": None,
                "tools_count": 2,
                "tool_names": ["query", "get_schema"],
                "description": "Execute governed queries and inspect schema definitions on PostgreSQL instances.",
                "features": ["Schema inspection", "Read-only queries", "Connection pooling"],
                "requires_approval": True,
                "server_config": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]},
            }
        ]

    return {
        "servers": server_list
    }


@router.get("/mcp/portal/request-status/{request_id}", response_model=MCPPortalRequestStatusResponse)
async def get_request_status(
    request_id: uuid.UUID,
    email: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.models.agentic import ApprovalRequest
    from app.models.governance import ClientApiKey
    from fastapi import HTTPException, status
    
    # 1. Lookup the ApprovalRequest
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
        
    # 2. Verify email matches (simple authentication)
    if request.user_name.lower() != email.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email does not match request")
        
    response_data = {
        "status": request.status,
    }
    
    # 3. If approved, find the generated API key and config
    if request.status == "approved":
        # We auto-provisioned the key with a description containing the request_id
        search_desc = f"Auto-provisioned from MCP Access Request: {request.id}"
        key_result = await db.execute(
            select(ClientApiKey).where(
                ClientApiKey.tenant_id == request.tenant_id,
                ClientApiKey.description == search_desc
            ).limit(1)
        )
        api_key_record = key_result.scalar_one_or_none()
        
        if api_key_record and api_key_record.key_encrypted:
            from app.services.client_api_key_service import decrypt_client_key
            raw_key = decrypt_client_key(api_key_record.key_encrypted)
            response_data["api_key"] = raw_key
            
            # Generate MCP Config block
            response_data["mcp_config"] = {
                "mcpServers": {
                    "pysetu-mcp": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-pysetu"],
                        "env": {
                            "PYSETU_API_KEY": raw_key,
                            "PYSETU_API_URL": "https://api.pysetu.ai"
                        }
                    }
                }
            }
            
    return response_data
