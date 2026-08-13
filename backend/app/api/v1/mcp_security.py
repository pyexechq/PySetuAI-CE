import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import MANAGE_MCP, require_permission
from app.db.session import get_db
from app.models.governance import MCPServer
from app.models.tenant import User
from app.schemas.governance import McpSsoInjectionConfigRequest, McpSsoInjectionConfigResponse, McpToolDenyRuleRequest, McpToolDenyRuleResponse
from app.services.mcp_security_service import add_deny_rule, get_sso_config, list_deny_rules, remove_deny_rule, upsert_sso_config

router = APIRouter()
_require_mcp_admin = require_permission(MANAGE_MCP)


async def _server(db: AsyncSession, tenant_id: uuid.UUID, server_id: str) -> MCPServer:
    try:
        parsed_id = uuid.UUID(server_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid server id") from exc
    result = await db.execute(select(MCPServer).where(MCPServer.id == parsed_id, MCPServer.tenant_id == tenant_id))
    server = result.scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


def _sso_response(config, server_id: uuid.UUID) -> McpSsoInjectionConfigResponse:
    return McpSsoInjectionConfigResponse(server_id=str(server_id), enabled=config.enabled, header_name=config.header_name, header_format=config.header_format, claim_extract=config.claim_extract, updated_at=config.updated_at.isoformat() if config.updated_at else "")


@router.get("/mcp/servers/{server_id}/sso-injection", response_model=McpSsoInjectionConfigResponse)
async def get_sso_injection(server_id: str, current_user: Annotated[User, Depends(_require_mcp_admin)], db: Annotated[AsyncSession, Depends(get_db)]) -> McpSsoInjectionConfigResponse:
    server = await _server(db, current_user.tenant_id, server_id)
    config = await get_sso_config(db, current_user.tenant_id, server.id)
    return _sso_response(config or type("DefaultConfig", (), {"enabled": False, "header_name": "Authorization", "header_format": "Bearer {token}", "claim_extract": "", "updated_at": None})(), server.id)


@router.put("/mcp/servers/{server_id}/sso-injection", response_model=McpSsoInjectionConfigResponse)
async def put_sso_injection(server_id: str, payload: McpSsoInjectionConfigRequest, current_user: Annotated[User, Depends(_require_mcp_admin)], db: Annotated[AsyncSession, Depends(get_db)]) -> McpSsoInjectionConfigResponse:
    server = await _server(db, current_user.tenant_id, server_id)
    try:
        config = await upsert_sso_config(db, current_user.tenant_id, server.id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _sso_response(config, server.id)


@router.get("/rbac/tool-deny-lists", response_model=list[McpToolDenyRuleResponse])
async def get_tool_deny_lists(current_user: Annotated[User, Depends(_require_mcp_admin)], db: Annotated[AsyncSession, Depends(get_db)]) -> list[McpToolDenyRuleResponse]:
    return [McpToolDenyRuleResponse(id=str(rule.id), role=rule.role, server_id=str(rule.server_id), tool_name=rule.tool_name, reason=rule.reason, server_name=name, created_at=rule.created_at.isoformat()) for rule, name in await list_deny_rules(db, current_user.tenant_id)]


@router.post("/rbac/tool-deny-lists", response_model=McpToolDenyRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_tool_deny_list(payload: McpToolDenyRuleRequest, current_user: Annotated[User, Depends(_require_mcp_admin)], db: Annotated[AsyncSession, Depends(get_db)]) -> McpToolDenyRuleResponse:
    server = await _server(db, current_user.tenant_id, payload.server_id)
    try:
        rule = await add_deny_rule(db, current_user.tenant_id, payload.model_dump())
    except Exception as exc:
        await db.rollback()
        if "uq_mcp_tool_deny" in str(exc):
            raise HTTPException(status_code=409, detail="This tool is already denied for this role") from exc
        raise
    return McpToolDenyRuleResponse(id=str(rule.id), role=rule.role, server_id=str(rule.server_id), tool_name=rule.tool_name, reason=rule.reason, server_name=server.name, created_at=rule.created_at.isoformat())


@router.delete("/rbac/tool-deny-lists/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool_deny_list(rule_id: str, current_user: Annotated[User, Depends(_require_mcp_admin)], db: Annotated[AsyncSession, Depends(get_db)]) -> None:
    try:
        parsed_id = uuid.UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid deny rule id") from exc
    if not await remove_deny_rule(db, current_user.tenant_id, parsed_id):
        raise HTTPException(status_code=404, detail="Deny rule not found")