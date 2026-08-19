"""Endpoint, agent inventory, and unified security-event API for the agent control plane."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_client
from app.core.rbac import (
    MANAGE_AGENTS,
    VIEW_AGENTS,
    VIEW_AUDIT_LOGS,
    require_any_permission,
)
from app.db.session import get_db
from app.models.agentic import AgentInventory, ApprovalRequest, Endpoint, SecurityEvent
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
    SecurityEventIngestRequest,
    SecurityEventIngestResponse,
    SecurityEventResponse,
    SecurityEventSummary,
)
from app.services.agentic_service import (
    decide_approval,
    file_governance_rules_for_bundle,
    heartbeat_endpoint,
    list_approvals,
    record_security_event,
    register_endpoint,
    security_event_summary,
    upsert_agent,
)
from app.services.policy_bundle_service import get_tenant_default_bundle

router = APIRouter()

_require_agent_view = require_any_permission(MANAGE_AGENTS, VIEW_AGENTS)
_require_audit_view = require_any_permission(VIEW_AUDIT_LOGS, MANAGE_AGENTS)
_require_approval_action = require_any_permission(MANAGE_AGENTS)


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
) -> list[SecurityEvent]:
    result = await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.tenant_id == _user.tenant_id)
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/security-events/summary", response_model=SecurityEventSummary)
async def security_events_summary_route(
    _user: Annotated[User, Depends(_require_audit_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await security_event_summary(db, _user.tenant_id)


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
    _user: Annotated[User, Depends(_require_audit_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str = Query(default="pending", alias="status"),
) -> list[ApprovalRequest]:
    return await list_approvals(db, _user.tenant_id, status_filter)


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_route(
    approval_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    user: Annotated[User, Depends(_require_approval_action)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApprovalRequest:
    approval = await _load_approval(db, approval_id, user.tenant_id)
    updated = await decide_approval(db, approval, "approved", user.name or user.email, payload.reason)
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
