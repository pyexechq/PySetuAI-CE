"""Endpoint, agent inventory, and unified security-event API for the agent control plane."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_client, security
from app.core.security import decode_access_token
from app.core.rbac import (
    MANAGE_AGENTS,
    MANAGE_POLICIES,
    USE_MCP,
    USE_STUDIO,
    VIEW_AGENTS,
    VIEW_AUDIT_LOGS,
    require_any_permission,
)
from app.db.session import get_db
from app.models.agentic import AgentInventory, ApprovalRequest, Endpoint, SanctionedAiTool, SecurityEvent
from app.models.governance import ClientApiKey, PolicyBundle
from app.models.tenant import User
from app.schemas.agentic import (
    AgentPolicyResponse,
    AgentRegisterRequest,
    AgentResponse,
    ApprovalDecisionRequest,
    ApprovalRequestResponse,
    EndpointHeartbeatRequest,
    EndpointRegisterRequest,
    EndpointResponse,
    SanctionedAiToolCreateRequest,
    SanctionedAiToolResponse,
    SecurityEventIngestRequest,
    SecurityEventIngestResponse,
    SecurityEventResponse,
    SecurityEventSummary,
    MCPAccessRequestPayload,
)
from app.services.agentic_service import (
    add_sanctioned_tool,
    decide_approval,
    file_governance_rules_for_bundle,
    heartbeat_endpoint,
    list_approvals,
    list_sanctioned_tools,
    record_security_event,
    register_endpoint,
    remove_sanctioned_tool,
    security_event_summary,
    upsert_agent,
)
from app.services.client_api_key_service import resolve_client_api_key
from app.services.policy_bundle_service import get_tenant_default_bundle
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter()

_require_agent_view = require_any_permission(MANAGE_AGENTS, VIEW_AGENTS)
_require_audit_view = require_any_permission(VIEW_AUDIT_LOGS, MANAGE_AGENTS)
_require_approval_view = require_any_permission(VIEW_AUDIT_LOGS, MANAGE_AGENTS, USE_MCP, USE_STUDIO, MANAGE_POLICIES)
_require_approval_action = require_any_permission(MANAGE_AGENTS)


async def get_caller_tenant(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[uuid.UUID, str]:
    if credentials is not None and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = payload.get("sub")
            if user_id:
                user = await db.get(User, uuid.UUID(str(user_id)))
                if user and user.is_active:
                    return user.tenant_id, user.email or user.name or "User"
        except Exception:
            pass

        key = await resolve_client_api_key(db, credentials.credentials)
        if key is not None:
            return key.tenant_id, key.name or "Client Key"

    # Graceful fallback to default tenant for developer portal requests
    from app.models.tenant import Tenant
    res = await db.execute(select(Tenant).limit(1))
    t = res.scalar_one_or_none()
    if t:
        return t.id, "Portal Developer"

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token or API key")


@router.post("/endpoints", response_model=EndpointResponse, status_code=status.HTTP_201_CREATED)
async def register_endpoint_route(
    payload: EndpointRegisterRequest,
    client: Annotated[ClientApiKey, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Endpoint:
    endpoint = await register_endpoint(db, client.tenant_id, payload)
    await db.commit()
    return endpoint


@router.post("/endpoints/{endpoint_id}/heartbeat", response_model=EndpointResponse)
async def endpoint_heartbeat_route(
    endpoint_id: uuid.UUID,
    payload: EndpointHeartbeatRequest,
    client: Annotated[ClientApiKey, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Endpoint:
    endpoint = await db.get(Endpoint, endpoint_id)
    if endpoint is None or endpoint.tenant_id != client.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")
    updated = await heartbeat_endpoint(db, endpoint, payload.status, payload.agent_version)
    await db.commit()
    return updated


@router.get("/endpoints", response_model=list[EndpointResponse])
async def list_endpoints_route(
    _user: Annotated[User, Depends(_require_agent_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Endpoint]:
    result = await db.execute(
        select(Endpoint).where(Endpoint.tenant_id == _user.tenant_id).order_by(Endpoint.registered_at.desc())
    )
    return list(result.scalars().all())


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def upsert_agent_route(
    payload: AgentRegisterRequest,
    client: Annotated[ClientApiKey, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentInventory:
    agent = await upsert_agent(db, client.tenant_id, payload)
    await db.commit()
    return agent


@router.get("/agents", response_model=list[AgentResponse])
async def list_agents_route(
    _user: Annotated[User, Depends(_require_agent_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgentInventory]:
    result = await db.execute(
        select(AgentInventory).where(AgentInventory.tenant_id == _user.tenant_id).order_by(AgentInventory.risk_score.desc())
    )
    return list(result.scalars().all())


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent_route(
    agent_id: uuid.UUID,
    _user: Annotated[User, Depends(_require_agent_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentInventory:
    agent = await db.get(AgentInventory, agent_id)
    if agent is None or agent.tenant_id != _user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.post("/security-events/ingest", response_model=SecurityEventIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_security_event_route(
    payload: SecurityEventIngestRequest,
    client: Annotated[ClientApiKey, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SecurityEventIngestResponse:
    event, audit = await record_security_event(db, client.tenant_id, payload, actor=client.name)
    await db.commit()
    return SecurityEventIngestResponse(event_id=str(event.id), audit_log_id=str(audit.id))


@router.get("/security-events", response_model=list[SecurityEventResponse])
async def list_security_events_route(
    _user: Annotated[User, Depends(_require_audit_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=200, ge=1, le=1000),
    action: str | None = Query(default=None),
) -> list[SecurityEvent]:
    query = select(SecurityEvent).where(SecurityEvent.tenant_id == _user.tenant_id)
    if action:
        query = query.where(SecurityEvent.action == action)
    result = await db.execute(
        query.order_by(SecurityEvent.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/security-events/summary", response_model=SecurityEventSummary)
async def security_events_summary_route(
    _user: Annotated[User, Depends(_require_audit_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await security_event_summary(db, _user.tenant_id)


@router.get("/sanctioned-tools", response_model=list[SanctionedAiToolResponse])
async def list_sanctioned_tools_route(
    _user: Annotated[User, Depends(_require_agent_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SanctionedAiTool]:
    return await list_sanctioned_tools(db, _user.tenant_id)


@router.post("/sanctioned-tools", response_model=SanctionedAiToolResponse, status_code=status.HTTP_201_CREATED)
async def add_sanctioned_tool_route(
    payload: SanctionedAiToolCreateRequest,
    user: Annotated[User, Depends(_require_approval_action)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SanctionedAiTool:
    tool = await add_sanctioned_tool(db, user.tenant_id, payload.name, added_by=user.email)
    await db.commit()
    return tool


@router.delete("/sanctioned-tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_sanctioned_tool_route(
    tool_id: uuid.UUID,
    user: Annotated[User, Depends(_require_approval_action)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    removed = await remove_sanctioned_tool(db, user.tenant_id, tool_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sanctioned tool not found")
    await db.commit()


@router.get("/shadow-ai/summary")
async def get_shadow_ai_summary(
    user: Annotated[User, Depends(_require_agent_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return aggregated shadow AI fleet discovery metrics and risk indicators."""
    sanctioned = await list_sanctioned_tools(db, user.tenant_id)
    sanctioned_names = {t.name.lower() for t in sanctioned}

    stmt = select(SecurityEvent).where(SecurityEvent.tenant_id == user.tenant_id).limit(200)
    result = await db.execute(stmt)
    events = result.scalars().all()
    shadow_events = [e for e in events if e.event_type == "discovery" or getattr(e, "action", "") == "bypassed"]

    unsanctioned_detected: set[str] = set()
    for ev in shadow_events:
        meta = ev.metadata_json or {}
        tools = meta.get("unsanctioned_tools") or []
        for t in tools:
            if t.lower() not in sanctioned_names:
                unsanctioned_detected.add(t)

    return {
        "sanctioned_tools_count": len(sanctioned),
        "unsanctioned_tools_count": len(unsanctioned_detected),
        "unsanctioned_tools": sorted(list(unsanctioned_detected)),
        "total_shadow_ai_events": len(shadow_events),
        "fleet_workstations_monitored": len({ev.actor for ev in shadow_events if ev.actor}),
    }


@router.get("/agentic/policy", response_model=AgentPolicyResponse)
async def get_agent_policy_route(
    client: Annotated[ClientApiKey, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentPolicyResponse:
    bundle = await _load_bundle_for_client(db, client)
    return AgentPolicyResponse(version="1", rules=file_governance_rules_for_bundle(bundle))


async def _load_bundle_for_client(
    db: AsyncSession,
    client: ClientApiKey,
) -> PolicyBundle | None:
    if client.bundle_id:
        return await db.get(PolicyBundle, client.bundle_id)
    return await get_tenant_default_bundle(db, client.tenant_id)


@router.get("/approvals", response_model=list[ApprovalRequestResponse])
async def list_approvals_route(
    caller: Annotated[tuple[uuid.UUID, str], Depends(get_caller_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str = Query(default="pending", alias="status"),
) -> list[ApprovalRequest]:
    tenant_id, _ = caller
    return await list_approvals(db, tenant_id, status_filter)


@router.post("/approvals/mcp-access-request", response_model=ApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_access_request_route(
    payload: MCPAccessRequestPayload,
    caller: Annotated[tuple[uuid.UUID, str], Depends(get_caller_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApprovalRequest:
    tenant_id, caller_identifier = caller
    now = datetime.now(UTC)
    action_type = payload.action or "mcp_access_request"
    tool_name = payload.requested_mcp_tool or (payload.requested_mcp_tools[0] if payload.requested_mcp_tools else "MCP Portal")
    if action_type == "dlp_policy_exception":
        tool_name = "DLP Policy Engine"
    elif action_type == "break_glass_test":
        tool_name = "Break Glass Controller"

    req = ApprovalRequest(
        tenant_id=tenant_id,
        user_name=payload.requester_email or caller_identifier,
        tool=tool_name,
        action=action_type,
        resource=payload.policy_id or "mcp_catalog",
        policy_id=payload.policy_id,
        policy_name=payload.policy_name or "",
        reason=payload.reason,
        requested_mcp_tool=payload.requested_mcp_tool,
        requested_mcp_tools=payload.requested_mcp_tools or [],
        requested_bundle_id=payload.requested_bundle_id,
        status="pending",
        expires_at=now + timedelta(days=7),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_route(
    approval_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    user: Annotated[User, Depends(_require_approval_action)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApprovalRequest:
    approval = await _load_approval(db, approval_id, user.tenant_id)
    updated = await decide_approval(db, approval, "approved", user.name or user.email, payload.reason)
    
    if updated.action == "mcp_access_request":
        from app.services.client_api_key_service import generate_client_key, encrypt_client_key
        full_key, key_prefix, key_hash = generate_client_key()
        bundle_id = updated.requested_bundle_id
        if not bundle_id:
            default_b = await get_tenant_default_bundle(db, user.tenant_id)
            bundle_id = default_b.id if default_b else None

        record = ClientApiKey(
            tenant_id=user.tenant_id,
            name=f"Access Key for {updated.tool or updated.user_name}",
            description=f"Auto-provisioned from MCP Access Request ({updated.tool}): {updated.id}",
            key_prefix=key_prefix,
            key_hash=key_hash,
            key_encrypted=encrypt_client_key(full_key),
            bundle_id=bundle_id,
            is_active=True,
        )
        db.add(record)
        
    await db.commit()
    return updated


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalRequestResponse)
async def reject_route(
    approval_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    user: Annotated[User, Depends(_require_approval_action)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApprovalRequest:
    approval = await _load_approval(db, approval_id, user.tenant_id)
    updated = await decide_approval(db, approval, "rejected", user.name or user.email, payload.reason)
    await db.commit()
    return updated


async def _load_approval(
    db: AsyncSession,
    approval_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ApprovalRequest:
    approval = await db.get(ApprovalRequest, approval_id)
    if approval is None or approval.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")
    if approval.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval request already decided")
    return approval
