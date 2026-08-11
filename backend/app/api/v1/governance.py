import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.gateway import _gateway_counts
from app.config import settings
from app.core.date_range import default_last_n_days, parse_date_range
from app.core.deps import get_current_user
from app.core.rbac import (
    MANAGE_LLM_PROVIDERS,
    MANAGE_MCP,
    MANAGE_POLICIES,
    USE_STUDIO,
    VIEW_AUDIT_LOGS,
    require_any_permission,
    require_permission,
)
from app.db.session import get_db
from app.models.governance import AuditLog, LLMProvider, MCPServer, Policy, RoutingRule
from app.models.tenant import User
from app.schemas.governance import (
    AuditLogResponse,
    GatewayStatusResponse,
    IngressBindingResponse,
    LLMProviderCreateRequest,
    LLMProviderUpdateRequest,
    McpDiscoverToolsResponse,
    McpHealthCheckBatchResponse,
    McpHealthCheckResponse,
    MCPServerCreateRequest,
    MCPServerResponse,
    MCPServerUpdateRequest,
    McpToolInvokeRequest,
    McpToolInvokeResponse,
    PolicyCreateRequest,
    PolicyGraphLinkResponse,
    PolicyRuleResponse,
    PolicyRulesSaveRequest,
    PolicyTreeNode,
    PolicyUpdateRequest,
    ProviderRebalanceResponse,
    ProviderShareItem,
    RoutingModelResponse,
    RoutingRuleCreateRequest,
    RoutingRuleResponse,
    RoutingRuleUpdateRequest,
)
from app.services.integration_service import get_or_create_integration
from app.services.mcp_client_service import (
    apply_discovered_tools,
    apply_tool_invoke,
    discover_mcp_tools,
    invoke_mcp_tool,
)
from app.services.mcp_health_service import apply_health_result, probe_mcp_server
from app.services.policy_graph import build_ingress_bindings, resolve_policy_graph_node
from app.services.provider_metrics_service import rebalance_provider_percentages
from app.services.secrets_service import (
    GEMINI_SECRET,
    OPENAI_SECRET,
    provider_secret_status,
    set_provider_secret,
    set_tenant_secret,
)

router = APIRouter()

_require_policy_access = require_any_permission(MANAGE_POLICIES, USE_STUDIO)
_require_policy_admin = require_permission(MANAGE_POLICIES)
_require_mcp = require_permission(MANAGE_MCP)
_require_llm_access = require_any_permission(MANAGE_LLM_PROVIDERS, USE_STUDIO)
_require_llm_admin = require_permission(MANAGE_LLM_PROVIDERS)
_require_audit = require_permission(VIEW_AUDIT_LOGS)

ALLOWED_MCP_STATUSES = {"healthy", "degraded", "offline"}
ALLOWED_MCP_TRANSPORTS = {"sse", "stdio", "streamable_http"}


def _mcp_server_response(server: MCPServer) -> MCPServerResponse:
    tool_names = server.tool_names if isinstance(server.tool_names, list) else []
    config = server.connection_config if isinstance(server.connection_config, dict) else {}
    return MCPServerResponse(
        id=str(server.id),
        name=server.name,
        category=server.category,
        success_rate=server.success_rate,
        avg_latency=server.avg_latency_ms,
        total_calls=server.total_calls,
        status=server.status,
        tools=server.tools_count,
        tool_names=[str(name) for name in tool_names],
        endpoint_url=server.endpoint_url,
        transport=server.transport or "sse",
        connection_config=config,
        trust_score=server.trust_score,
        risk_score=server.risk_score,
    )


async def _get_mcp_server(db: AsyncSession, tenant_id: uuid.UUID, server_id: str) -> MCPServer:
    try:
        server_uuid = uuid.UUID(server_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid server id") from exc

    result = await db.execute(select(MCPServer).where(MCPServer.id == server_uuid, MCPServer.tenant_id == tenant_id))
    server = result.scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found")
    return server


def _normalize_tool_names(names: list[str] | None) -> list[str]:
    if not names:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in names:
        name = raw.strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(name)
    return normalized


def _normalize_connection_config(config: dict | None) -> dict:
    if not config:
        return {}
    normalized: dict = {}
    auth_header = config.get("auth_header")
    if isinstance(auth_header, str) and auth_header.strip():
        normalized["auth_header"] = auth_header.strip()
    timeout = config.get("timeout_sec")
    if timeout is not None:
        try:
            normalized["timeout_sec"] = max(5, min(int(timeout), 120))
        except (TypeError, ValueError):
            normalized["timeout_sec"] = 30
    return normalized


def _merge_connection_config(existing: dict | None, patch: dict | None) -> dict:
    merged = dict(existing or {})
    merged.update(_normalize_connection_config(patch))
    return merged


def _validate_transport(transport: str) -> str:
    value = transport.strip().lower()
    if value not in ALLOWED_MCP_TRANSPORTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"transport must be one of: {', '.join(sorted(ALLOWED_MCP_TRANSPORTS))}",
        )
    return value


async def _get_policy(db: AsyncSession, tenant_id: uuid.UUID, policy_id: str) -> Policy:
    try:
        policy_uuid = uuid.UUID(policy_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid policy id") from exc

    result = await db.execute(
        select(Policy).where(Policy.id == policy_uuid, Policy.tenant_id == tenant_id, Policy.policy_type == "policy")
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


def _build_policy_tree(policies: list[Policy], parent_id=None) -> list[PolicyTreeNode]:
    nodes: list[PolicyTreeNode] = []
    for policy in policies:
        if policy.parent_id == parent_id:
            children = _build_policy_tree(policies, policy.id)
            nodes.append(
                PolicyTreeNode(
                    id=str(policy.id),
                    label=policy.name,
                    type=policy.policy_type,
                    status=policy.status if policy.policy_type == "policy" else None,
                    children=children or None,
                )
            )
    return nodes


@router.get("/policies/tree", response_model=list[PolicyTreeNode])
async def get_policy_tree(
    current_user: Annotated[User, Depends(_require_policy_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PolicyTreeNode]:
    result = await db.execute(select(Policy).where(Policy.tenant_id == current_user.tenant_id))
    policies = list(result.scalars().all())
    return _build_policy_tree(policies)


@router.post("/policies", response_model=PolicyTreeNode, status_code=status.HTTP_201_CREATED)
async def create_policy(
    payload: PolicyCreateRequest,
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyTreeNode:

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Policy name is required")

    policy_type = payload.policy_type.strip().lower()
    if policy_type not in {"policy", "folder"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="policy_type must be 'policy' or 'folder'")

    status_value = payload.status.strip().lower()
    if policy_type == "policy" and status_value not in {"active", "draft", "disabled"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid policy status")

    parent_uuid: uuid.UUID | None = None
    if payload.parent_id:
        try:
            parent_id = uuid.UUID(payload.parent_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parent_id") from exc

        parent_result = await db.execute(
            select(Policy).where(
                Policy.id == parent_id,
                Policy.tenant_id == current_user.tenant_id,
                Policy.policy_type == "folder",
            )
        )
        parent = parent_result.scalar_one_or_none()
        if parent is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent folder not found")
        parent_uuid = parent.id

    policy = Policy(
        tenant_id=current_user.tenant_id,
        name=name,
        policy_type=policy_type,
        status=status_value if policy_type == "policy" else "active",
        parent_id=parent_uuid,
        rules=[] if policy_type == "policy" else None,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    return PolicyTreeNode(
        id=str(policy.id),
        label=policy.name,
        type=policy.policy_type,
        status=policy.status if policy.policy_type == "policy" else None,
        children=None,
    )


@router.put("/policies/{policy_id}", response_model=PolicyTreeNode)
async def update_policy(
    policy_id: str,
    payload: PolicyUpdateRequest,
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyTreeNode:
    policy = await _get_policy(db, current_user.tenant_id, policy_id)

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Policy name is required")
        existing = await db.execute(
            select(Policy).where(
                Policy.tenant_id == current_user.tenant_id,
                Policy.name.ilike(name),
                Policy.id != policy.id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Policy name already exists")
        policy.name = name

    if payload.status is not None:
        status_value = payload.status.strip().lower()
        if status_value not in {"active", "draft", "disabled"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid policy status")
        policy.status = status_value

    await db.commit()
    await db.refresh(policy)
    return PolicyTreeNode(
        id=str(policy.id),
        label=policy.name,
        type=policy.policy_type,
        status=policy.status if policy.policy_type == "policy" else None,
        children=None,
    )


@router.get("/policies/rules", response_model=list[PolicyRuleResponse])
async def get_policy_rules(
    current_user: Annotated[User, Depends(_require_policy_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    policy_id: str | None = Query(None, description="Policy UUID; defaults to Prompt Injection Guard"),
) -> list[PolicyRuleResponse]:
    if policy_id:
        policy = await _get_policy(db, current_user.tenant_id, policy_id)
    else:
        result = await db.execute(
            select(Policy).where(
                Policy.tenant_id == current_user.tenant_id,
                Policy.name == "Prompt Injection Guard",
            )
        )
        policy = result.scalar_one_or_none()
    if not policy or not policy.rules:
        return []
    return [PolicyRuleResponse(**rule) for rule in policy.rules]


@router.get("/policies/{policy_id}/rules", response_model=list[PolicyRuleResponse])
async def get_policy_rules_by_id(
    policy_id: str,
    current_user: Annotated[User, Depends(_require_policy_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PolicyRuleResponse]:
    policy = await _get_policy(db, current_user.tenant_id, policy_id)
    if not policy.rules:
        return []
    return [PolicyRuleResponse(**rule) for rule in policy.rules]


@router.put("/policies/{policy_id}/rules", response_model=list[PolicyRuleResponse])
async def save_policy_rules(
    policy_id: str,
    payload: PolicyRulesSaveRequest,
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PolicyRuleResponse]:
    policy = await _get_policy(db, current_user.tenant_id, policy_id)

    allowed_severities = {"low", "medium", "high", "critical"}
    allowed_actions = {"Block", "Redact", "Alert", "Allow"}
    saved_rules: list[dict] = []

    for rule in payload.rules:
        name = rule.name.strip()
        condition = rule.condition.strip()
        if not name or not condition:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each rule requires name and condition")
        severity = rule.severity.strip().lower()
        if severity not in allowed_severities:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid severity: {rule.severity}")
        if rule.action not in allowed_actions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid action: {rule.action}")

        saved_rules.append(
            {
                "id": rule.id.strip() or f"r-{uuid.uuid4().hex[:8]}",
                "name": name,
                "condition": condition,
                "action": rule.action,
                "severity": severity,
                "enabled": rule.enabled,
            }
        )

    policy.rules = saved_rules
    await db.commit()
    await db.refresh(policy)
    return [PolicyRuleResponse(**rule) for rule in policy.rules]


@router.post("/policies/seed-starter-rules", response_model=dict)
async def seed_starter_policy_rules(
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    policy_id: str | None = Query(None, description="Optional policy UUID to backfill only one policy"),
) -> dict:
    """Backfill starter rules for known seeded policies that have no rules yet."""
    from app.db.seed_governance import POLICY_RULE_SETS

    query = select(Policy).where(
        Policy.tenant_id == current_user.tenant_id,
        Policy.policy_type == "policy",
    )
    if policy_id:
        policy = await _get_policy(db, current_user.tenant_id, policy_id)
        policies = [policy]
    else:
        result = await db.execute(query)
        policies = list(result.scalars().all())

    updated = 0
    for policy in policies:
        starter = POLICY_RULE_SETS.get(policy.name)
        if not starter or policy.rules:
            continue
        policy.rules = starter
        updated += 1
    if updated:
        await db.commit()
    return {"policies_updated": updated, "message": f"Applied starter rules to {updated} policy(ies)."}


@router.get("/policies/graph-links", response_model=list[PolicyGraphLinkResponse])
async def get_policy_graph_links(
    current_user: Annotated[User, Depends(_require_policy_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    node_id: str | None = Query(None, description="Filter by governance graph node id"),
) -> list[PolicyGraphLinkResponse]:
    result = await db.execute(
        select(Policy).where(
            Policy.tenant_id == current_user.tenant_id,
            Policy.policy_type == "policy",
        )
    )
    links: list[PolicyGraphLinkResponse] = []
    for policy in result.scalars().all():
        mapping = resolve_policy_graph_node(policy.name)
        if node_id and mapping["graph_node_id"] != node_id:
            continue
        links.append(
            PolicyGraphLinkResponse(
                policy_id=str(policy.id),
                policy_name=policy.name,
                policy_status=policy.status,
                graph_node_id=mapping["graph_node_id"],
                graph_node_label=mapping["graph_node_label"],
                graph_node_type=mapping["graph_node_type"],
                edge_labels=mapping["edge_labels"],
                description=mapping["description"],
            )
        )
    return links


@router.get("/governance/ingress-bindings", response_model=list[IngressBindingResponse])
async def get_ingress_bindings(
    current_user: Annotated[User, Depends(_require_policy_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[IngressBindingResponse]:
    bindings = await build_ingress_bindings(db, current_user.tenant_id)
    return [IngressBindingResponse(**item) for item in bindings]


@router.get("/mcp/servers", response_model=list[MCPServerResponse])
async def list_mcp_servers(
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MCPServerResponse]:
    result = await db.execute(
        select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id).order_by(MCPServer.total_calls.desc())
    )
    return [_mcp_server_response(s) for s in result.scalars().all()]


@router.post("/mcp/servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    payload: MCPServerCreateRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MCPServerResponse:
    name = payload.name.strip()
    category = payload.category.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Server name is required")
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category is required")

    status_value = payload.status.strip().lower()
    if status_value not in ALLOWED_MCP_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"status must be one of: {', '.join(sorted(ALLOWED_MCP_STATUSES))}",
        )

    existing = await db.execute(
        select(MCPServer).where(
            MCPServer.tenant_id == current_user.tenant_id,
            MCPServer.name.ilike(name),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MCP server name already exists")

    tool_names = _normalize_tool_names(payload.tool_names)
    transport = _validate_transport(payload.transport)
    endpoint_url = payload.endpoint_url.strip() if payload.endpoint_url else None
    server = MCPServer(
        tenant_id=current_user.tenant_id,
        name=name,
        category=category,
        status=status_value,
        tool_names=tool_names,
        tools_count=len(tool_names),
        endpoint_url=endpoint_url or None,
        transport=transport,
        connection_config=_normalize_connection_config(payload.connection_config),
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return _mcp_server_response(server)


@router.put("/mcp/servers/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: str,
    payload: MCPServerUpdateRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MCPServerResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Server name is required")
        existing = await db.execute(
            select(MCPServer).where(
                MCPServer.tenant_id == current_user.tenant_id,
                MCPServer.name.ilike(name),
                MCPServer.id != server.id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MCP server name already exists")
        server.name = name

    if payload.category is not None:
        category = payload.category.strip()
        if not category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category is required")
        server.category = category

    if payload.status is not None:
        status_value = payload.status.strip().lower()
        if status_value not in ALLOWED_MCP_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"status must be one of: {', '.join(sorted(ALLOWED_MCP_STATUSES))}",
            )
        server.status = status_value

    if payload.tool_names is not None:
        tool_names = _normalize_tool_names(payload.tool_names)
        server.tool_names = tool_names
        server.tools_count = len(tool_names)

    if payload.endpoint_url is not None:
        server.endpoint_url = payload.endpoint_url.strip() or None

    if payload.transport is not None:
        server.transport = _validate_transport(payload.transport)

    if payload.connection_config is not None:
        server.connection_config = _merge_connection_config(server.connection_config, payload.connection_config)

    await db.commit()
    await db.refresh(server)
    return _mcp_server_response(server)


@router.delete("/mcp/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: str,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    await db.delete(server)
    await db.commit()


def _health_check_response(server: MCPServer, result) -> McpHealthCheckResponse:
    return McpHealthCheckResponse(
        server_id=str(server.id),
        server_name=server.name,
        status=server.status if result.skipped else result.status,
        ok=result.ok,
        latency_ms=result.latency_ms,
        message=result.message,
        http_status=result.http_status,
        skipped=result.skipped,
        checked_at=datetime.now(UTC).isoformat(),
    )


@router.post("/mcp/servers/{server_id}/health-check", response_model=McpHealthCheckResponse)
async def check_mcp_server_health(
    server_id: str,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpHealthCheckResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    result = await probe_mcp_server(server)
    apply_health_result(server, result)
    await db.commit()
    await db.refresh(server)
    return _health_check_response(server, result)


@router.post("/mcp/servers/health-check-all", response_model=McpHealthCheckBatchResponse)
async def check_all_mcp_servers_health(
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpHealthCheckBatchResponse:
    result = await db.execute(
        select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id).order_by(MCPServer.name.asc())
    )
    servers = result.scalars().all()

    responses: list[McpHealthCheckResponse] = []
    healthy = degraded = offline = skipped = 0

    for server in servers:
        probe = await probe_mcp_server(server)
        apply_health_result(server, probe)
        response = _health_check_response(server, probe)
        responses.append(response)
        if probe.skipped:
            skipped += 1
        elif probe.status == "healthy":
            healthy += 1
        elif probe.status == "degraded":
            degraded += 1
        else:
            offline += 1

    await db.commit()
    return McpHealthCheckBatchResponse(
        results=responses,
        healthy=healthy,
        degraded=degraded,
        offline=offline,
        skipped=skipped,
    )


@router.post("/mcp/servers/{server_id}/discover-tools", response_model=McpDiscoverToolsResponse)
async def discover_mcp_server_tools(
    server_id: str,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpDiscoverToolsResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    result = await discover_mcp_tools(server)
    apply_discovered_tools(server, result)
    await db.commit()
    await db.refresh(server)
    return McpDiscoverToolsResponse(
        server_id=str(server.id),
        server_name=server.name,
        ok=result.ok,
        tool_names=result.tool_names if result.ok else list(server.tool_names or []),
        tools_count=len(result.tool_names) if result.ok else server.tools_count,
        tool_schemas=result.tool_schemas or list((server.connection_config or {}).get("tool_schemas") or []),
        message=result.message,
        latency_ms=result.latency_ms,
        skipped=result.skipped,
        checked_at=datetime.now(UTC).isoformat(),
    )


@router.post("/mcp/servers/{server_id}/tools/invoke", response_model=McpToolInvokeResponse)
async def invoke_mcp_server_tool(
    server_id: str,
    payload: McpToolInvokeRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpToolInvokeResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    result = await invoke_mcp_tool(server, payload.tool_name, payload.arguments)
    apply_tool_invoke(server, result)
    await db.commit()
    await db.refresh(server)
    session = (server.connection_config or {}).get("mcp_session") or {}
    return McpToolInvokeResponse(
        server_id=str(server.id),
        server_name=server.name,
        ok=result.ok,
        message=result.message,
        result=result.result,
        latency_ms=result.latency_ms,
        skipped=result.skipped,
        session_reused=bool(session.get("reused")),
        checked_at=datetime.now(UTC).isoformat(),
    )


async def _validate_routing_target_model(db: AsyncSession, tenant_id: uuid.UUID, target_model: str) -> None:
    if target_model.lower() == "default":
        return
    providers = await db.execute(
        select(LLMProvider.name).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
        )
    )
    names = {name.lower() for (name,) in providers.all()}
    if target_model.lower() not in names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target model must match an active registered LLM provider",
        )


@router.get("/audit/logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    current_user: Annotated[User, Depends(_require_audit)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(None),
    status: str | None = Query(None),
    since: str | None = Query(None, description="Return entries after this timestamp (YYYY-MM-DD HH:MM:SS)"),
    from_date: str | None = Query(None, description="Inclusive start date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Inclusive end date (YYYY-MM-DD)"),
    limit: int = Query(200, ge=1, le=1000),
) -> list[AuditLogResponse]:
    from datetime import datetime

    range_start, range_end = parse_date_range(from_date, to_date)
    if range_start is None and range_end is None:
        range_start, range_end = default_last_n_days(7)

    query = (
        select(AuditLog)
        .where(
            AuditLog.tenant_id == current_user.tenant_id,
            AuditLog.timestamp >= range_start,
            AuditLog.timestamp < range_end,
        )
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )
    if status and status != "all":
        query = query.where(AuditLog.status == status)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                AuditLog.actor.ilike(term),
                AuditLog.action.ilike(term),
                AuditLog.resource.ilike(term),
                AuditLog.details.ilike(term),
            )
        )
    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            query = query.where(AuditLog.timestamp > since_dt)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="since must be formatted as YYYY-MM-DD HH:MM:SS",
            ) from exc
    result = await db.execute(query)
    logs = result.scalars().all()
    items = [
        AuditLogResponse(
            id=str(log.id),
            timestamp=log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            actor=log.actor,
            action=log.action,
            resource=log.resource,
            status=log.status,
            risk=log.risk,
            details=log.details,
        )
        for log in logs
    ]
    return items


async def _provider_response(db: AsyncSession, tenant_id: uuid.UUID, provider: LLMProvider) -> RoutingModelResponse:
    api_key_set, api_key_masked = await provider_secret_status(db, tenant_id, provider)
    return RoutingModelResponse(
        id=str(provider.id),
        model=provider.name,
        provider_type=provider.provider_type,
        requests=provider.total_requests,
        percentage=provider.percentage,
        latency=provider.avg_latency_ms,
        success_rate=provider.success_rate,
        is_active=provider.is_active,
        api_key_set=api_key_set,
        api_key_masked=api_key_masked,
    )


async def _apply_provider_api_key(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    provider_type: str,
    provider: LLMProvider,
    api_key: str | None,
) -> None:
    if api_key is None:
        return

    trimmed = api_key.strip()
    if not trimmed:
        await set_provider_secret(db, tenant_id, provider, None)
        return

    await set_provider_secret(db, tenant_id, provider, trimmed)
    integration = await get_or_create_integration(db, tenant_id)
    if provider_type in {"openai", "azure", "anthropic", "custom"}:
        await set_tenant_secret(db, tenant_id, OPENAI_SECRET, trimmed)
    elif provider_type == "gemini":
        await set_tenant_secret(db, tenant_id, GEMINI_SECRET, trimmed)
    elif provider_type == "ollama":
        integration.ollama_enabled = True


async def _get_provider_or_404(db: AsyncSession, tenant_id: uuid.UUID, provider_id: str) -> LLMProvider:
    try:
        provider_uuid = uuid.UUID(provider_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider id") from exc

    result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.id == provider_uuid,
            LLMProvider.tenant_id == tenant_id,
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return provider


ALLOWED_PROVIDER_TYPES = {"openai", "gemini", "anthropic", "ollama", "azure", "custom"}


@router.get("/llm/providers", response_model=list[RoutingModelResponse])
async def list_llm_providers(
    current_user: Annotated[User, Depends(_require_llm_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RoutingModelResponse]:
    result = await db.execute(
        select(LLMProvider)
        .where(LLMProvider.tenant_id == current_user.tenant_id)
        .order_by(LLMProvider.percentage.desc(), LLMProvider.name.asc())
    )
    return [await _provider_response(db, current_user.tenant_id, provider) for provider in result.scalars().all()]


@router.post("/llm/providers/rebalance-percentages", response_model=ProviderRebalanceResponse)
async def rebalance_llm_provider_percentages(
    current_user: Annotated[User, Depends(_require_llm_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderRebalanceResponse:
    total_requests, updates = await rebalance_provider_percentages(db, current_user.tenant_id)
    if total_requests <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No gateway traffic recorded yet — percentages unchanged",
        )

    await db.commit()
    return ProviderRebalanceResponse(
        total_requests=total_requests,
        providers=[ProviderShareItem(**item) for item in updates],
        message=f"Updated routing shares for {len(updates)} active provider(s) from live traffic.",
    )


@router.post("/llm/providers", response_model=RoutingModelResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_provider(
    payload: LLMProviderCreateRequest,
    current_user: Annotated[User, Depends(_require_llm_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoutingModelResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider name is required")

    provider_type = payload.provider_type.strip().lower()
    if provider_type not in ALLOWED_PROVIDER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"provider_type must be one of: {', '.join(sorted(ALLOWED_PROVIDER_TYPES))}",
        )

    existing = await db.execute(
        select(LLMProvider).where(
            LLMProvider.tenant_id == current_user.tenant_id,
            LLMProvider.name.ilike(name),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Provider name already exists")

    provider = LLMProvider(
        tenant_id=current_user.tenant_id,
        name=name,
        provider_type=provider_type,
        is_active=payload.is_active,
    )
    db.add(provider)
    await _apply_provider_api_key(db, current_user.tenant_id, provider_type, provider, payload.api_key)
    await db.commit()
    await db.refresh(provider)
    return await _provider_response(db, current_user.tenant_id, provider)


@router.put("/llm/providers/{provider_id}", response_model=RoutingModelResponse)
async def update_llm_provider(
    provider_id: str,
    payload: LLMProviderUpdateRequest,
    current_user: Annotated[User, Depends(_require_llm_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoutingModelResponse:
    provider = await _get_provider_or_404(db, current_user.tenant_id, provider_id)

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider name is required")
        duplicate = await db.execute(
            select(LLMProvider).where(
                LLMProvider.tenant_id == current_user.tenant_id,
                LLMProvider.name.ilike(name),
                LLMProvider.id != provider.id,
            )
        )
        if duplicate.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Provider name already exists")
        provider.name = name

    if payload.provider_type is not None:
        provider_type = payload.provider_type.strip().lower()
        if provider_type not in ALLOWED_PROVIDER_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"provider_type must be one of: {', '.join(sorted(ALLOWED_PROVIDER_TYPES))}",
            )
        provider.provider_type = provider_type

    if payload.is_active is not None:
        provider.is_active = payload.is_active

    if payload.percentage is not None:
        if payload.percentage < 0 or payload.percentage > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="percentage must be 0–100")
        provider.percentage = payload.percentage

    await _apply_provider_api_key(db, current_user.tenant_id, provider.provider_type, provider, payload.api_key)

    await db.commit()
    await db.refresh(provider)
    return await _provider_response(db, current_user.tenant_id, provider)


@router.delete("/llm/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_provider(
    provider_id: str,
    current_user: Annotated[User, Depends(_require_llm_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    provider = await _get_provider_or_404(db, current_user.tenant_id, provider_id)
    provider.is_active = False
    await db.commit()


ALLOWED_RULE_STATUSES = {"active", "draft", "disabled"}


def _rule_response(rule: RoutingRule) -> RoutingRuleResponse:
    return RoutingRuleResponse(
        id=str(rule.id),
        name=rule.name,
        priority=rule.priority,
        condition=rule.condition,
        target_model=rule.target_model,
        status=rule.status,
    )


async def _get_rule_or_404(db: AsyncSession, tenant_id: uuid.UUID, rule_id: str) -> RoutingRule:
    try:
        rule_uuid = uuid.UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid rule id") from exc

    result = await db.execute(
        select(RoutingRule).where(RoutingRule.id == rule_uuid, RoutingRule.tenant_id == tenant_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing rule not found")
    return rule


@router.get("/llm/routing-rules", response_model=list[RoutingRuleResponse])
async def list_routing_rules(
    current_user: Annotated[User, Depends(_require_llm_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RoutingRuleResponse]:
    result = await db.execute(
        select(RoutingRule).where(RoutingRule.tenant_id == current_user.tenant_id).order_by(RoutingRule.priority.asc())
    )
    return [_rule_response(r) for r in result.scalars().all()]


@router.post("/llm/routing-rules", response_model=RoutingRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_routing_rule(
    payload: RoutingRuleCreateRequest,
    current_user: Annotated[User, Depends(_require_llm_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoutingRuleResponse:
    name = payload.name.strip()
    condition = payload.condition.strip()
    target_model = payload.target_model.strip()
    if not name or not condition or not target_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Name, condition, and target model are required"
        )

    status_value = payload.status.strip().lower()
    if status_value not in ALLOWED_RULE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"status must be one of: {', '.join(sorted(ALLOWED_RULE_STATUSES))}",
        )

    await _validate_routing_target_model(db, current_user.tenant_id, target_model)

    rule = RoutingRule(
        tenant_id=current_user.tenant_id,
        name=name,
        priority=payload.priority,
        condition=condition,
        target_model=target_model,
        status=status_value,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_response(rule)


@router.put("/llm/routing-rules/{rule_id}", response_model=RoutingRuleResponse)
async def update_routing_rule(
    rule_id: str,
    payload: RoutingRuleUpdateRequest,
    current_user: Annotated[User, Depends(_require_llm_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoutingRuleResponse:
    rule = await _get_rule_or_404(db, current_user.tenant_id, rule_id)

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rule name is required")
        rule.name = name

    if payload.condition is not None:
        condition = payload.condition.strip()
        if not condition:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Condition is required")
        rule.condition = condition

    if payload.target_model is not None:
        target_model = payload.target_model.strip()
        if not target_model:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target model is required")
        await _validate_routing_target_model(db, current_user.tenant_id, target_model)
        rule.target_model = target_model

    if payload.priority is not None:
        rule.priority = payload.priority

    if payload.status is not None:
        status_value = payload.status.strip().lower()
        if status_value not in ALLOWED_RULE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"status must be one of: {', '.join(sorted(ALLOWED_RULE_STATUSES))}",
            )
        rule.status = status_value

    await db.commit()
    await db.refresh(rule)
    return _rule_response(rule)


@router.delete("/llm/routing-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_rule(
    rule_id: str,
    current_user: Annotated[User, Depends(_require_llm_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    rule = await _get_rule_or_404(db, current_user.tenant_id, rule_id)
    await db.delete(rule)
    await db.commit()


@router.get("/gateway/status", response_model=GatewayStatusResponse)
async def get_gateway_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GatewayStatusResponse:
    from app.services.integration_service import resolve_gateway_config
    from app.services.opa_service import check_opa_health

    total, blocked = await _gateway_counts(db, current_user.tenant_id)
    config = await resolve_gateway_config(db, current_user.tenant_id)
    opa_available, _ = await check_opa_health()
    return GatewayStatusResponse(
        status="operational",
        openai_compatible=True,
        gemini_compatible=True,
        requests_today=max(total, 0),
        blocked_today=max(blocked, 0),
        endpoints=[
            "/v1/chat/completions",
            "/api/v1/v1/chat/completions",
            "/v1/models",
            "/v1beta/models/{model}:generateContent",
        ],
        proxy_mode=config.upstream,
        opa_enabled=settings.opa_enabled,
        opa_available=opa_available and settings.opa_enabled,
    )
