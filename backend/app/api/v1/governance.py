import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.gateway import _gateway_counts
from app.config import settings
from app.core.date_range import default_last_n_days, parse_date_range
from app.core.deps import get_current_user
from app.core.rbac import (
    MANAGE_LLM_PROVIDERS,
    MANAGE_MCP,
    MANAGE_POLICIES,
    USE_MCP,
    USE_STUDIO,
    VIEW_AUDIT_LOGS,
    require_any_permission,
    require_permission,
)
from app.db.session import get_db
from app.models.governance import (
    AuditLog,
    AuditLogBody,
    ClientApiKey,
    LLMProvider,
    MCPServer,
    Policy,
    PolicyBundle,
    RoutingGroup,
    RoutingRule,
    RoutingRuleClientKey,
)
from app.models.tenant import Tenant, User
from app.schemas.governance import (
    AuditLogResponse,
    AuditLogBodyResponse,
    RequestLogSettingsResponse,
    RequestLogSettingsUpdateRequest,
    RequestLogPurgeResponse,
    GatewayStatusResponse,
    IngressBindingResponse,
    LLMProviderCreateRequest,
    LLMProviderUpdateRequest,
    McpDiscoverToolsResponse,
    DynamicToolPreviewRequest,
    DynamicToolPreviewResponse,
    DynamicToolSettingsResponse,
    DynamicToolSettingsUpdate,
    McpCatalogCustomInstallRequest,
    McpCatalogEntryResponse,
    McpCatalogInstallRequest,
    McpCatalogListResponse,
    McpOAuthListResponse,
    McpOAuthServerStatusResponse,
    McpOAuthStatusResponse,
    McpOAuthUpsertRequest,
    McpToolRiskInventoryResponse,
    McpToolRiskItem,
    McpToolRiskSettingsUpdate,
    McpToolRiskUpdateRequest,
    McpAgentDetectRequest,
    McpAgentDetectResponse,
    McpAgentItem,
    McpAgentServerAccess,
    McpAgentSettingsResponse,
    McpAgentSettingsUpdate,
    McpAgentServerAccessUpdate,
    McpPortalConnectRequest,
    McpPortalConnectResponse,
    McpUrlFilterProbeRequest,
    McpUrlFilterProbeResponse,
    McpUrlFilterSettingsResponse,
    McpUrlFilterSettingsUpdate,
    McpSpecParseRequest,
    McpSpecParseResponse,
    McpPortalListResponse,
    McpPortalEntry,
    McpPortalSettingsResponse,
    McpPortalSettingsUpdate,
    McpPortalVisibilityUpdate,
    McpMultiplexInfoResponse,
    McpHealthCheckBatchResponse,
    McpHealthCheckResponse,
    MCPServerCreateRequest,
    MCPServerResponse,
    MCPServerUpdateRequest,
    McpToolInvokeRequest,
    McpToolInvokeResponse,
    PolicyAssistRequest,
    PolicyAssistResponse,
    PolicyConditionHelpExample,
    PolicyCreateRequest,
    PolicyGraphLinkResponse,
    PolicyRuleResponse,
    PolicyRulesSaveRequest,
    PolicyTestRequest,
    PolicyTreeNode,
    PolicyUpdateRequest,
    ProviderRebalanceResponse,
    ProviderShareItem,
    RoutingModelResponse,
    RoutingRuleCreateRequest,
    RoutingRuleResponse,
    RoutingRuleUpdateRequest,
)
from app.schemas.access import ClientApiKeyResponse
from app.schemas.openai import InspectionResult
from app.services.client_api_key_service import client_key_response, get_client_api_key
from app.services.integration_service import get_or_create_integration
from app.services.policy_engine import _evaluate_rules
from app.services.request_log_service import (
    get_request_log_body,
    get_request_log_settings,
    purge_expired_request_logs,
    update_request_log_retention,
)
from app.services.mcp_agent_service import (
    apply_allowed_agents_to_config,
    detect_agent,
    filter_servers_for_agent,
    is_mcp_enabled_for_agent,
    merge_agent_toggles,
    public_agent_settings,
    toggles_from_tenant,
)
from app.services.mcp_tool_risk_service import (
    annotate_tools,
    apply_policies_to_config,
    merge_tool_policies,
    policies_from_config,
    tool_is_visible,
)
from app.services.dynamic_tool_service import (
    apply_dynamic_tools_for_request,
    catalog_from_servers,
    tool_token_estimate,
    tools_from_server,
)
from app.services.mcp_client_service import (
    apply_discovered_tools,
    apply_tool_invoke,
    discover_mcp_tools,
    invoke_mcp_tool,
)
from app.services.mcp_catalog_service import (
    catalog_slug_installed,
    custom_install_spec,
    get_catalog_entry,
    install_spec_from_entry,
    list_catalog_entries,
)
from app.services.mcp_health_service import apply_health_result, probe_mcp_server
from app.services.policy_graph import build_ingress_bindings, resolve_policy_graph_node
from app.services.provider_metrics_service import rebalance_provider_percentages
from app.services.mcp_oauth_broker_service import (
    delete_oauth_state,
    fetch_and_apply_token,
    load_oauth_state,
    persist_token_state,
    public_oauth_status,
    save_oauth_state,
)
from app.services.mcp_portal_service import (
    connect_user_token,
    disconnect_user,
    list_portal_entries,
    portal_visible,
    resolve_effective_mcp_access_token,
    set_portal_visible,
    tenant_has_token,
    user_has_token,
    connection_status,
    server_auth_required,
)
from app.services.mcp_url_filter_service import (
    evaluate_tool_access,
    merge_url_filters,
    probe_url,
    public_url_filters,
)
from app.services.mcp_spec_proxy_service import parse_spec
from app.services.secrets_service import (
    GEMINI_SECRET,
    MCP_URL_FILTER_VENDOR_KEY,
    OPENAI_SECRET,
    get_tenant_secret,
    provider_secret_status,
    secrets_backend_name,
    set_provider_secret,
    set_tenant_secret,
)

router = APIRouter()

_require_policy_access = require_any_permission(MANAGE_POLICIES, USE_STUDIO)
_require_policy_admin = require_permission(MANAGE_POLICIES)
_require_mcp = require_permission(MANAGE_MCP)
_require_mcp_portal = require_any_permission(USE_MCP, MANAGE_MCP)
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
    catalog_slug = config.get("catalog_slug")
    if isinstance(catalog_slug, str) and catalog_slug.strip():
        normalized["catalog_slug"] = catalog_slug.strip().lower()
    command = config.get("command")
    if isinstance(command, str) and command.strip():
        normalized["command"] = command.strip()
    args = config.get("args")
    if isinstance(args, list):
        normalized["args"] = [str(item) for item in args]
    tool_risk = config.get("tool_risk")
    if isinstance(tool_risk, dict):
        normalized["tool_risk"] = tool_risk
    allowed_agents = config.get("allowed_agents")
    if isinstance(allowed_agents, list):
        normalized["allowed_agents"] = [str(item) for item in allowed_agents]
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


async def _ensure_unique_mcp_name(db: AsyncSession, tenant_id: uuid.UUID, name: str) -> None:
    existing = await db.execute(
        select(MCPServer).where(
            MCPServer.tenant_id == tenant_id,
            MCPServer.name.ilike(name),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MCP server name already exists")


async def _create_mcp_server_from_spec(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    spec: dict,
) -> MCPServer:
    name = spec["name"].strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Server name is required")
    await _ensure_unique_mcp_name(db, tenant_id, name)
    tool_names = _normalize_tool_names(spec.get("tool_names") or [])
    transport = _validate_transport(str(spec.get("transport") or "sse"))
    endpoint_url = spec.get("endpoint_url")
    if isinstance(endpoint_url, str):
        endpoint_url = endpoint_url.strip() or None
    else:
        endpoint_url = None
    status_value = str(spec.get("status") or "offline").strip().lower()
    if status_value not in ALLOWED_MCP_STATUSES:
        status_value = "offline"
    server = MCPServer(
        tenant_id=tenant_id,
        name=name,
        category=str(spec.get("category") or "Custom").strip() or "Custom",
        status=status_value,
        tool_names=tool_names,
        tools_count=len(tool_names),
        endpoint_url=endpoint_url,
        transport=transport,
        connection_config=_normalize_connection_config(spec.get("connection_config")),
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


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


@router.get("/policies/condition-help", response_model=list[PolicyConditionHelpExample])
async def get_policy_condition_help(
    current_user: Annotated[User, Depends(_require_policy_access)],
) -> list[PolicyConditionHelpExample]:
    from app.services.policy_assist_service import list_condition_help_examples

    return list_condition_help_examples()


@router.post("/policies/assist", response_model=PolicyAssistResponse)
async def assist_policy_building(
    payload: PolicyAssistRequest,
    current_user: Annotated[User, Depends(_require_policy_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyAssistResponse:
    from app.services.policy_assist_service import suggest_policy_rules_with_ai

    result = await suggest_policy_rules_with_ai(
        db,
        current_user.tenant_id,
        goal=payload.goal,
        policy_name=payload.policy_name,
        existing_rule_names=payload.existing_rule_names,
    )
    return PolicyAssistResponse(**result)


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


class SeedComplianceTemplateRequest(BaseModel):
    template_id: str

@router.post("/policies/seed-compliance-template", response_model=dict)
async def seed_compliance_template(
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: SeedComplianceTemplateRequest,
) -> dict:
    """Seed a compliance template (e.g. gdpr, hipaa) to the tenant's policy tree."""
    from app.db.seed_governance import COMPLIANCE_TEMPLATES
    
    template = COMPLIANCE_TEMPLATES.get(body.template_id)
    if not template:
        raise HTTPException(status_code=400, detail="Invalid template ID")
        
    folder_name = template["folder_name"]
    policy_name = template["policy_name"]
    rules = template["rules"]
    
    # 1. Find or create the folder
    folder_query = select(Policy).where(
        Policy.tenant_id == current_user.tenant_id,
        Policy.policy_type == "folder",
        Policy.name == folder_name,
    )
    folder_result = await db.execute(folder_query)
    folder = folder_result.scalar_one_or_none()
    
    if not folder:
        folder = Policy(
            tenant_id=current_user.tenant_id,
            name=folder_name,
            policy_type="folder",
            status="active",
        )
        db.add(folder)
        await db.flush()
        
    # 2. Check if the policy already exists
    policy_query = select(Policy).where(
        Policy.tenant_id == current_user.tenant_id,
        Policy.policy_type == "policy",
        Policy.name == policy_name,
    )
    policy_result = await db.execute(policy_query)
    policy = policy_result.scalar_one_or_none()
    
    if policy:
        return {"message": f"Policy '{policy_name}' already exists in your workspace."}
        
    # 3. Create the policy
    new_policy = Policy(
        tenant_id=current_user.tenant_id,
        name=policy_name,
        policy_type="policy",
        status="active",
        parent_id=folder.id,
        rules=rules,
    )
    db.add(new_policy)
    await db.commit()
    
    return {"message": f"Successfully applied '{policy_name}' template."}


@router.post("/policies/test", response_model=InspectionResult)
async def test_policy_rules(
    payload: PolicyTestRequest,
    _current_user: Annotated[User, Depends(_require_policy_access)],
) -> InspectionResult:
    # Convert Pydantic models back to dicts for _evaluate_rules
    rules_dicts = [rule.model_dump() for rule in payload.rules]
    result = _evaluate_rules(payload.content, rules_dicts)
    return result


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


@router.post("/mcp/servers/parse-spec", response_model=McpSpecParseResponse)
async def parse_mcp_spec(
    payload: McpSpecParseRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
) -> McpSpecParseResponse:
    """Parse an OpenAPI / Postman / GraphQL spec into MCP tool definitions (BL-083)."""
    try:
        result = await parse_spec(payload.protocol, payload.spec_url, payload.spec_text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return McpSpecParseResponse(**result)


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
    token = await resolve_effective_mcp_access_token(db, server, user_id=current_user.id)
    result = await probe_mcp_server(server, access_token=token)
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
        token = await resolve_effective_mcp_access_token(db, server, user_id=current_user.id)
        probe = await probe_mcp_server(server, access_token=token)
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
    token = await resolve_effective_mcp_access_token(db, server, user_id=current_user.id)
    result = await discover_mcp_tools(server, access_token=token)
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


@router.get("/mcp/dynamic-tools/settings", response_model=DynamicToolSettingsResponse)
async def get_dynamic_tool_settings(
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DynamicToolSettingsResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    servers_result = await db.execute(select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id))
    catalog = catalog_from_servers(
        list(servers_result.scalars().all()),
        auto_hide_destructive=bool(tenant.mcp_auto_hide_destructive),
    )
    return DynamicToolSettingsResponse(
        enabled=tenant.dynamic_tool_calling_enabled,
        max_tools=tenant.dynamic_tool_max,
        catalog_count=len(catalog),
        catalog_tokens=tool_token_estimate(catalog),
    )


@router.put("/mcp/dynamic-tools/settings", response_model=DynamicToolSettingsResponse)
async def update_dynamic_tool_settings(
    payload: DynamicToolSettingsUpdate,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DynamicToolSettingsResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    if payload.enabled is not None:
        tenant.dynamic_tool_calling_enabled = payload.enabled
    if payload.max_tools is not None:
        tenant.dynamic_tool_max = max(1, min(int(payload.max_tools), 64))
    await db.commit()
    await db.refresh(tenant)
    servers_result = await db.execute(select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id))
    catalog = catalog_from_servers(
        list(servers_result.scalars().all()),
        auto_hide_destructive=bool(tenant.mcp_auto_hide_destructive),
    )
    return DynamicToolSettingsResponse(
        enabled=tenant.dynamic_tool_calling_enabled,
        max_tools=tenant.dynamic_tool_max,
        catalog_count=len(catalog),
        catalog_tokens=tool_token_estimate(catalog),
    )


@router.get("/mcp/multiplex", response_model=McpMultiplexInfoResponse)
async def get_mcp_multiplex_info(
    request: Request,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpMultiplexInfoResponse:
    from app.services.mcp_multiplex_service import build_multiplex_catalog, multiplex_public_path

    servers_result = await db.execute(select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id))
    servers = list(servers_result.scalars().all())
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    catalog = build_multiplex_catalog(servers, auto_hide_destructive=bool(tenant.mcp_auto_hide_destructive))
    base = str(request.base_url).rstrip("/")
    public_path = multiplex_public_path()
    api_path = "/api/v1/mcp"
    return McpMultiplexInfoResponse(
        url=f"{base}{public_path}",
        api_url=f"{base}{api_path}",
        auth="Authorization: Bearer <client API key or JWT>",
        tool_namespace="server_slug__tool_name",
        server_count=len(servers),
        tool_count=len(catalog),
        sample_tools=[t["name"] for t in catalog[:8]],
        instructions=(
            "Point the MCP client at the multiplex URL with the same PySetu client API key used for /v1/chat/completions. "
            "tools/list returns every registered server's tools with a server prefix. tools/call routes to the backing MCP server."
        ),
    )


@router.get("/mcp/catalog", response_model=McpCatalogListResponse)
async def list_mcp_catalog(
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpCatalogListResponse:
    servers_result = await db.execute(select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id))
    servers = list(servers_result.scalars().all())
    entries = []
    for raw in list_catalog_entries():
        entries.append(
            McpCatalogEntryResponse(
                slug=raw["slug"],
                name=raw["name"],
                description=raw["description"],
                category=raw["category"],
                transport=raw["transport"],
                default_endpoint=raw.get("default_endpoint"),
                tool_names=list(raw.get("tool_names") or []),
                auth_required=bool(raw.get("auth_required")),
                vendor=str(raw.get("vendor") or ""),
                installed=catalog_slug_installed(servers, raw["slug"]),
            )
        )
    return McpCatalogListResponse(entries=entries)


@router.post("/mcp/catalog/{slug}/install", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def install_mcp_catalog_entry(
    slug: str,
    payload: McpCatalogInstallRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MCPServerResponse:
    entry = get_catalog_entry(slug)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog entry not found")
    servers_result = await db.execute(select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id))
    if catalog_slug_installed(list(servers_result.scalars().all()), entry["slug"]):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Catalog entry is already installed")
    spec = install_spec_from_entry(
        entry,
        endpoint_url=payload.endpoint_url,
        name=payload.name,
    )
    server = await _create_mcp_server_from_spec(db, current_user.tenant_id, spec)
    return _mcp_server_response(server)


@router.post("/mcp/catalog/custom", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def install_custom_mcp_server(
    payload: McpCatalogCustomInstallRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MCPServerResponse:
    try:
        spec = custom_install_spec(
            name=payload.name,
            endpoint_url=payload.endpoint_url,
            transport=payload.transport,
            category=payload.category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    server = await _create_mcp_server_from_spec(db, current_user.tenant_id, spec)
    return _mcp_server_response(server)


def _oauth_status_payload(state, *, server_id: str | None = None, server_name: str | None = None):
    body = public_oauth_status(state)
    body["secrets_backend"] = secrets_backend_name()
    if server_id is not None:
        return McpOAuthServerStatusResponse(server_id=server_id, server_name=server_name or "", **body)
    return McpOAuthStatusResponse(**body)


@router.get("/mcp/oauth", response_model=McpOAuthListResponse)
async def list_mcp_oauth(
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpOAuthListResponse:
    result = await db.execute(
        select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id).order_by(MCPServer.name.asc())
    )
    servers = list(result.scalars().all())
    items: list[McpOAuthServerStatusResponse] = []
    for server in servers:
        state = await load_oauth_state(db, current_user.tenant_id, server.id)
        items.append(_oauth_status_payload(state, server_id=str(server.id), server_name=server.name))
    return McpOAuthListResponse(servers=items, secrets_backend=secrets_backend_name())


@router.get("/mcp/servers/{server_id}/oauth", response_model=McpOAuthStatusResponse)
async def get_mcp_oauth(
    server_id: str,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpOAuthStatusResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    state = await load_oauth_state(db, current_user.tenant_id, server.id)
    return _oauth_status_payload(state)


@router.put("/mcp/servers/{server_id}/oauth", response_model=McpOAuthStatusResponse)
async def upsert_mcp_oauth(
    server_id: str,
    payload: McpOAuthUpsertRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpOAuthStatusResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    try:
        state = await save_oauth_state(db, current_user.tenant_id, server.id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _oauth_status_payload(state)


@router.post("/mcp/servers/{server_id}/oauth/refresh", response_model=McpOAuthStatusResponse)
async def refresh_mcp_oauth(
    server_id: str,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpOAuthStatusResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    state = await load_oauth_state(db, current_user.tenant_id, server.id)
    if state is None or not state.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OAuth credentials are not configured")
    try:
        updated = await fetch_and_apply_token(state)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Token refresh failed: {exc}") from exc
    await persist_token_state(db, current_user.tenant_id, server.id, updated)
    return _oauth_status_payload(updated)


@router.delete("/mcp/servers/{server_id}/oauth", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_oauth(
    server_id: str,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    await delete_oauth_state(db, current_user.tenant_id, server.id)


@router.get("/mcp/tool-risk", response_model=McpToolRiskInventoryResponse)
async def list_mcp_tool_risk(
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpToolRiskInventoryResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    auto_hide = bool(tenant.mcp_auto_hide_destructive)
    servers_result = await db.execute(
        select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id).order_by(MCPServer.name.asc())
    )
    items: list[McpToolRiskItem] = []
    for server in servers_result.scalars().all():
        policies = policies_from_config(server.connection_config)
        for tool in annotate_tools(tools_from_server(server), policies, auto_hide_destructive=auto_hide):
            items.append(
                McpToolRiskItem(
                    server_id=str(server.id),
                    server_name=server.name,
                    name=tool["name"],
                    description=str(tool.get("description") or ""),
                    risk=tool["risk"],
                    hidden=bool(tool["hidden"]),
                    auto_hidden=bool(tool["auto_hidden"]),
                    visible=bool(tool["visible"]),
                )
            )
    return McpToolRiskInventoryResponse(
        auto_hide_destructive=auto_hide,
        tools=items,
        visible_count=sum(1 for item in items if item.visible),
        hidden_count=sum(1 for item in items if not item.visible),
    )


@router.put("/mcp/tool-risk/settings", response_model=McpToolRiskInventoryResponse)
async def update_mcp_tool_risk_settings(
    payload: McpToolRiskSettingsUpdate,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpToolRiskInventoryResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    tenant.mcp_auto_hide_destructive = payload.auto_hide_destructive
    await db.commit()
    return await list_mcp_tool_risk(current_user, db)


@router.put("/mcp/servers/{server_id}/tool-risk", response_model=McpToolRiskInventoryResponse)
async def update_mcp_server_tool_risk(
    server_id: str,
    payload: McpToolRiskUpdateRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpToolRiskInventoryResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    try:
        merged = merge_tool_policies(policies_from_config(server.connection_config), [item.model_dump() for item in payload.tools])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    server.connection_config = apply_policies_to_config(server.connection_config, merged)
    await db.commit()
    return await list_mcp_tool_risk(current_user, db)


async def _mcp_agent_settings_payload(tenant: Tenant, servers: list[MCPServer]) -> McpAgentSettingsResponse:
    toggles = toggles_from_tenant(tenant.mcp_agent_toggles)
    server_rows: list[McpAgentServerAccess] = []
    for server in servers:
        config = server.connection_config if isinstance(server.connection_config, dict) else {}
        allowed = config.get("allowed_agents")
        allowed_list = [str(item) for item in allowed] if isinstance(allowed, list) else []
        server_rows.append(
            McpAgentServerAccess(
                server_id=str(server.id),
                server_name=server.name,
                allowed_agents=allowed_list,
            )
        )
    return McpAgentSettingsResponse(agents=public_agent_settings(toggles), servers=server_rows)


@router.get("/mcp/agent-settings", response_model=McpAgentSettingsResponse)
async def get_mcp_agent_settings(
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpAgentSettingsResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    servers_result = await db.execute(
        select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id).order_by(MCPServer.name.asc())
    )
    return await _mcp_agent_settings_payload(tenant, list(servers_result.scalars().all()))


@router.put("/mcp/agent-settings", response_model=McpAgentSettingsResponse)
async def update_mcp_agent_settings(
    payload: McpAgentSettingsUpdate,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpAgentSettingsResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    tenant.mcp_agent_toggles = merge_agent_toggles(tenant.mcp_agent_toggles, payload.toggles)
    await db.commit()
    await db.refresh(tenant)
    servers_result = await db.execute(
        select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id).order_by(MCPServer.name.asc())
    )
    return await _mcp_agent_settings_payload(tenant, list(servers_result.scalars().all()))


@router.put("/mcp/servers/{server_id}/allowed-agents", response_model=McpAgentSettingsResponse)
async def update_mcp_server_allowed_agents(
    server_id: str,
    payload: McpAgentServerAccessUpdate,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpAgentSettingsResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    server.connection_config = apply_allowed_agents_to_config(server.connection_config, payload.allowed_agents)
    await db.commit()
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    servers_result = await db.execute(
        select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id).order_by(MCPServer.name.asc())
    )
    return await _mcp_agent_settings_payload(tenant, list(servers_result.scalars().all()))


@router.post("/mcp/agents/detect", response_model=McpAgentDetectResponse)
async def detect_mcp_agent(
    payload: McpAgentDetectRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpAgentDetectResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    toggles = toggles_from_tenant(tenant.mcp_agent_toggles)
    agent = detect_agent(payload.user_agent, payload.metadata)
    labels = {item["slug"]: item["label"] for item in public_agent_settings(toggles)}
    return McpAgentDetectResponse(
        agent=agent,
        mcp_enabled=is_mcp_enabled_for_agent(toggles, agent),
        label=labels.get(agent, agent),
    )


@router.get("/mcp/portal", response_model=McpPortalListResponse)
async def list_mcp_portal(
    request: Request,
    current_user: Annotated[User, Depends(_require_mcp_portal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpPortalListResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    servers_result = await db.execute(
        select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id).order_by(MCPServer.name.asc())
    )
    servers = list(servers_result.scalars().all())
    toggles = toggles_from_tenant(tenant.mcp_agent_toggles)
    agent = detect_agent(None, None)
    servers = filter_servers_for_agent(servers, agent, toggles)
    raw_entries = await list_portal_entries(db, current_user, tenant, servers)
    entries = [McpPortalEntry(**item) for item in raw_entries]
    from app.services.mcp_multiplex_service import multiplex_public_path

    base = str(request.base_url).rstrip("/")
    multiplex_url = f"{base}{multiplex_public_path()}"
    return McpPortalListResponse(
        enabled=bool(tenant.mcp_portal_enabled),
        multiplex_url=multiplex_url,
        entries=entries,
    )


@router.get("/mcp/portal/settings", response_model=McpPortalSettingsResponse)
async def get_mcp_portal_settings(
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpPortalSettingsResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    return McpPortalSettingsResponse(enabled=bool(tenant.mcp_portal_enabled))


@router.put("/mcp/portal/settings", response_model=McpPortalSettingsResponse)
async def update_mcp_portal_settings(
    payload: McpPortalSettingsUpdate,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpPortalSettingsResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    tenant.mcp_portal_enabled = bool(payload.enabled)
    await db.commit()
    return McpPortalSettingsResponse(enabled=bool(tenant.mcp_portal_enabled))


@router.put("/mcp/servers/{server_id}/portal-visibility", response_model=MCPServerResponse)
async def update_mcp_server_portal_visibility(
    server_id: str,
    payload: McpPortalVisibilityUpdate,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MCPServerResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    set_portal_visible(server, payload.portal_visible)
    await db.commit()
    await db.refresh(server)
    return _mcp_server_response(server)


@router.post("/mcp/portal/{server_id}/connect", response_model=McpPortalConnectResponse)
async def connect_mcp_portal_server(
    server_id: str,
    payload: McpPortalConnectRequest,
    current_user: Annotated[User, Depends(_require_mcp_portal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpPortalConnectResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    if not tenant.mcp_portal_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MCP portal is disabled for this tenant")
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    if not portal_visible(server):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration is not available in the portal")
    try:
        await connect_user_token(db, current_user, server, payload.access_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    user_connected = await user_has_token(db, tenant.id, current_user.id, server.id)
    tenant_connected = await tenant_has_token(db, server)
    status_label = connection_status(
        server,
        user_connected=user_connected,
        tenant_token_available=tenant_connected,
    )
    from app.services.mcp_portal_service import load_user_connection

    row = await load_user_connection(db, current_user.id, server.id)
    connected_at = row.connected_at.isoformat() if row and row.connected_at else datetime.now(UTC).isoformat()
    return McpPortalConnectResponse(
        server_id=str(server.id),
        connection_status=status_label,
        connected_at=connected_at,
    )


@router.delete("/mcp/portal/{server_id}/connect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_mcp_portal_server(
    server_id: str,
    current_user: Annotated[User, Depends(_require_mcp_portal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    if not await disconnect_user(db, current_user, server_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No personal connection found")


async def _url_filter_vendor_key(db: AsyncSession, tenant_id) -> str | None:
    return await get_tenant_secret(db, tenant_id, MCP_URL_FILTER_VENDOR_KEY)


@router.get("/mcp/url-filters", response_model=McpUrlFilterSettingsResponse)
async def get_mcp_url_filters(
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpUrlFilterSettingsResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    vendor_key = await _url_filter_vendor_key(db, tenant.id)
    body = public_url_filters(tenant.mcp_url_filters, vendor_configured=bool(vendor_key))
    return McpUrlFilterSettingsResponse(**body)


@router.put("/mcp/url-filters", response_model=McpUrlFilterSettingsResponse)
async def update_mcp_url_filters(
    payload: McpUrlFilterSettingsUpdate,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpUrlFilterSettingsResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    current = merge_url_filters(tenant.mcp_url_filters)
    updates = payload.model_dump(exclude_unset=True)
    vendor_api_key = updates.pop("vendor_api_key", None)
    current.update({key: value for key, value in updates.items() if key in current})
    tenant.mcp_url_filters = current
    if vendor_api_key is not None:
        await set_tenant_secret(db, tenant.id, MCP_URL_FILTER_VENDOR_KEY, vendor_api_key or None)
    await db.commit()
    vendor_key = await _url_filter_vendor_key(db, tenant.id)
    body = public_url_filters(tenant.mcp_url_filters, vendor_configured=bool(vendor_key))
    return McpUrlFilterSettingsResponse(**body)


@router.post("/mcp/url-filters/probe", response_model=McpUrlFilterProbeResponse)
async def probe_mcp_url_filter(
    payload: McpUrlFilterProbeRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpUrlFilterProbeResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    result = probe_url(payload.url, tenant.mcp_url_filters or {})
    return McpUrlFilterProbeResponse(**result)


@router.post("/mcp/dynamic-tools/preview", response_model=DynamicToolPreviewResponse)
async def preview_dynamic_tools(
    payload: DynamicToolPreviewRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DynamicToolPreviewResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    servers_result = await db.execute(select(MCPServer).where(MCPServer.tenant_id == current_user.tenant_id))
    max_tools = payload.max_tools or tenant.dynamic_tool_max
    result = apply_dynamic_tools_for_request(
        list(servers_result.scalars().all()),
        payload.query,
        None,
        enabled=True,
        max_tools=max_tools,
        auto_hide_destructive=bool(tenant.mcp_auto_hide_destructive),
    )
    return DynamicToolPreviewResponse(
        enabled=tenant.dynamic_tool_calling_enabled,
        catalog_count=result.catalog_count,
        selected_count=result.selected_count,
        selected_names=result.selected_names,
        original_tokens=result.original_tokens,
        compressed_tokens=result.compressed_tokens,
        tokens_saved=result.tokens_saved,
        savings_pct=result.savings_pct,
    )


@router.post("/mcp/servers/{server_id}/tools/invoke", response_model=McpToolInvokeResponse)
async def invoke_mcp_server_tool(
    server_id: str,
    payload: McpToolInvokeRequest,
    current_user: Annotated[User, Depends(_require_mcp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> McpToolInvokeResponse:
    server = await _get_mcp_server(db, current_user.tenant_id, server_id)
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one()
    if not tool_is_visible(server, payload.tool_name, auto_hide_destructive=bool(tenant.mcp_auto_hide_destructive)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tool is hidden by risk policy")
    vendor_key = await _url_filter_vendor_key(db, tenant.id)
    allowed, reason = await evaluate_tool_access(
        payload.tool_name,
        payload.arguments,
        tenant.mcp_url_filters or {},
        vendor_api_key=vendor_key,
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason or "URL blocked by policy")
    token = await resolve_effective_mcp_access_token(db, server, user_id=current_user.id)
    result = await invoke_mcp_tool(server, payload.tool_name, payload.arguments, access_token=token)
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


async def _validate_routing_target_model(db: AsyncSession, tenant_id: uuid.UUID, target_model: str) -> str:
    requested_models = [model.strip() for model in target_model.split(",")]
    if not requested_models or any(not model for model in requested_models):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target model must match an active registered LLM provider",
        )
    providers = await db.execute(
        select(LLMProvider.name).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
        )
    )
    provider_names = {name.lower(): name for (name,) in providers.all()}
    canonical_models = [provider_names.get(model.lower()) for model in requested_models]
    if any(model is None for model in canonical_models):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target model must match an active registered LLM provider",
        )
    return ", ".join(model for model in canonical_models if model is not None)


@router.get("/audit/logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    current_user: Annotated[User, Depends(_require_audit)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(None),
    audit_id: str | None = Query(None, description="Exact audit log UUID"),
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
    if audit_id:
        try:
            query = query.where(AuditLog.id == uuid.UUID(audit_id.strip()))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="audit_id must be a valid UUID",
            ) from exc
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
    log_ids = [log.id for log in logs]
    body_ids: set[uuid.UUID] = set()
    if log_ids:
        body_result = await db.execute(
            select(AuditLogBody.audit_log_id).where(
                AuditLogBody.tenant_id == current_user.tenant_id,
                AuditLogBody.audit_log_id.in_(log_ids),
            )
        )
        body_ids = set(body_result.scalars().all())
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
            has_request_log=log.id in body_ids,
        )
        for log in logs
    ]
    return items


@router.get("/audit/logs/{audit_id}/body", response_model=AuditLogBodyResponse)
async def get_audit_log_body(
    audit_id: str,
    current_user: Annotated[User, Depends(_require_audit)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogBodyResponse:
    try:
        audit_uuid = uuid.UUID(audit_id.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="audit_id must be a valid UUID",
        ) from exc
    body = await get_request_log_body(db, current_user.tenant_id, audit_uuid)
    if body is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request log body not found")
    return AuditLogBodyResponse(
        audit_log_id=str(body.audit_log_id),
        request_payload=body.request_payload,
        response_payload=body.response_payload,
        guardrail_events=body.guardrail_events,
        tool_events=body.tool_events,
        created_at=body.created_at.strftime("%Y-%m-%d %H:%M:%S") if body.created_at else None,
    )


@router.get("/audit/request-log-settings", response_model=RequestLogSettingsResponse)
async def read_request_log_settings(
    current_user: Annotated[User, Depends(_require_audit)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestLogSettingsResponse:
    payload = await get_request_log_settings(db, current_user.tenant_id)
    return RequestLogSettingsResponse(**payload)


@router.put("/audit/request-log-settings", response_model=RequestLogSettingsResponse)
async def update_request_log_settings(
    body: RequestLogSettingsUpdateRequest,
    current_user: Annotated[User, Depends(_require_audit)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestLogSettingsResponse:
    payload = await update_request_log_retention(db, current_user.tenant_id, body.retention_days)
    await db.commit()
    return RequestLogSettingsResponse(**payload)


@router.post("/audit/purge-request-logs", response_model=RequestLogPurgeResponse)
async def purge_request_logs(
    current_user: Annotated[User, Depends(_require_audit)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestLogPurgeResponse:
    purged = await purge_expired_request_logs(db, current_user.tenant_id)
    await db.commit()
    stored = await get_request_log_settings(db, current_user.tenant_id)
    return RequestLogPurgeResponse(purged=purged, stored_entries=stored["stored_entries"])


async def _provider_response(db: AsyncSession, tenant_id: uuid.UUID, provider: LLMProvider) -> RoutingModelResponse:
    api_key_set, api_key_masked = await provider_secret_status(db, tenant_id, provider)
    return RoutingModelResponse(
        id=str(provider.id),
        model=provider.name,
        provider_type=provider.provider_type,
        endpoint_url=provider.endpoint_url,
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


def _normalize_provider_endpoint(endpoint: str | None) -> str | None:
    if endpoint is None:
        return None
    trimmed = endpoint.strip()
    return trimmed or None


def _validate_provider_endpoint(provider_type: str, endpoint_url: str | None) -> str | None:
    normalized = _normalize_provider_endpoint(endpoint_url)
    if provider_type == "custom":
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="endpoint_url is required for custom providers",
            )
        if not normalized.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="endpoint_url must start with http:// or https://",
            )
    return normalized


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
        endpoint_url=_validate_provider_endpoint(provider_type, payload.endpoint_url),
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

    if payload.endpoint_url is not None or payload.provider_type is not None:
        effective_type = (payload.provider_type or provider.provider_type).strip().lower()
        endpoint_value = payload.endpoint_url if payload.endpoint_url is not None else provider.endpoint_url
        provider.endpoint_url = _validate_provider_endpoint(effective_type, endpoint_value)
        if effective_type != "custom":
            provider.endpoint_url = None

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
    provider_name = (provider.name or "").strip().lower()

    await set_provider_secret(db, current_user.tenant_id, provider, None)

    groups = await db.execute(
        select(RoutingGroup).where(RoutingGroup.tenant_id == current_user.tenant_id)
    )
    for group in groups.scalars().all():
        members = list(group.members or [])
        filtered = [
            member
            for member in members
            if not (
                isinstance(member, dict)
                and str(member.get("model") or member.get("name") or "").strip().lower() == provider_name
            )
        ]
        if len(filtered) != len(members):
            group.members = filtered

    await db.delete(provider)
    await db.commit()


ALLOWED_RULE_STATUSES = {"active", "draft", "disabled"}
ALLOWED_RESPONSE_FORMATS = {"openai", "anthropic", "vertex", "auto"}


def _rule_response(rule: RoutingRule) -> RoutingRuleResponse:
    return RoutingRuleResponse(
        id=str(rule.id),
        name=rule.name,
        priority=rule.priority,
        condition=rule.condition,
        target_model=rule.target_model,
        status=rule.status,
        response_format=rule.response_format,
    )


async def _bundle_names_for_keys(db: AsyncSession, tenant_id: uuid.UUID, keys: list[ClientApiKey]) -> dict[str, str]:
    bundle_ids = [k.bundle_id for k in keys if k.bundle_id]
    if not bundle_ids:
        return {}
    result = await db.execute(
        select(PolicyBundle).where(PolicyBundle.id.in_(bundle_ids), PolicyBundle.tenant_id == tenant_id)
    )
    return {str(b.id): b.name for b in result.scalars().all()}


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

    response_format = payload.response_format.strip().lower()
    if response_format not in ALLOWED_RESPONSE_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"response_format must be one of: {', '.join(sorted(ALLOWED_RESPONSE_FORMATS))}",
        )

    target_model = await _validate_routing_target_model(db, current_user.tenant_id, target_model)

    rule = RoutingRule(
        tenant_id=current_user.tenant_id,
        name=name,
        priority=payload.priority,
        condition=condition,
        target_model=target_model,
        status=status_value,
        response_format=response_format,
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
        rule.target_model = await _validate_routing_target_model(db, current_user.tenant_id, target_model)

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

    if payload.response_format is not None:
        response_format = payload.response_format.strip().lower()
        if response_format not in ALLOWED_RESPONSE_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"response_format must be one of: {', '.join(sorted(ALLOWED_RESPONSE_FORMATS))}",
            )
        rule.response_format = response_format

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


# ── BL-088: per-rule client API key assignment ──────────────────────────────


@router.get("/llm/routing-rules/{rule_id}/client-keys", response_model=list[ClientApiKeyResponse])
async def list_routing_rule_client_keys(
    rule_id: str,
    current_user: Annotated[User, Depends(_require_llm_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ClientApiKeyResponse]:
    rule = await _get_rule_or_404(db, current_user.tenant_id, rule_id)
    result = await db.execute(
        select(ClientApiKey)
        .join(RoutingRuleClientKey, RoutingRuleClientKey.client_api_key_id == ClientApiKey.id)
        .where(RoutingRuleClientKey.routing_rule_id == rule.id, ClientApiKey.tenant_id == current_user.tenant_id)
    )
    keys = result.scalars().all()
    bundle_names = await _bundle_names_for_keys(db, current_user.tenant_id, keys)
    return [
        ClientApiKeyResponse(**client_key_response(k, bundle_name=bundle_names.get(str(k.bundle_id)) if k.bundle_id else None))
        for k in keys
    ]


@router.post(
    "/llm/routing-rules/{rule_id}/client-keys/{key_id}",
    response_model=list[ClientApiKeyResponse],
    status_code=status.HTTP_201_CREATED,
)
async def assign_routing_rule_client_key(
    rule_id: str,
    key_id: str,
    current_user: Annotated[User, Depends(_require_llm_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ClientApiKeyResponse]:
    rule = await _get_rule_or_404(db, current_user.tenant_id, rule_id)
    key = await get_client_api_key(db, current_user.tenant_id, key_id)

    existing = await db.execute(
        select(RoutingRuleClientKey).where(
            RoutingRuleClientKey.routing_rule_id == rule.id,
            RoutingRuleClientKey.client_api_key_id == key.id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(RoutingRuleClientKey(routing_rule_id=rule.id, client_api_key_id=key.id))
        await db.commit()

    return await list_routing_rule_client_keys(rule_id, current_user, db)


@router.delete(
    "/llm/routing-rules/{rule_id}/client-keys/{key_id}",
    response_model=list[ClientApiKeyResponse],
)
async def unassign_routing_rule_client_key(
    rule_id: str,
    key_id: str,
    current_user: Annotated[User, Depends(_require_llm_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ClientApiKeyResponse]:
    rule = await _get_rule_or_404(db, current_user.tenant_id, rule_id)
    key = await get_client_api_key(db, current_user.tenant_id, key_id)

    await db.execute(
        delete(RoutingRuleClientKey).where(
            RoutingRuleClientKey.routing_rule_id == rule.id,
            RoutingRuleClientKey.client_api_key_id == key.id,
        )
    )
    await db.commit()

    return await list_routing_rule_client_keys(rule_id, current_user, db)


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
            "/api/v1/chat/completions",
            "/v1/models",
            "/api/v1/models",
            "/v1/mcp",
            "/api/v1/mcp",
            "/v1beta/models/{model}:generateContent",
        ],
        proxy_mode=config.upstream,
        opa_enabled=settings.opa_enabled,
        opa_available=opa_available and settings.opa_enabled,
    )
