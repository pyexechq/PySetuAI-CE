"""Request/response contracts for MCP governance depth (Phase 3)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ToolPolicyAction = Literal["allow", "approval", "block"]


class MCPToolPolicyUpsertRequest(BaseModel):
    server_id: uuid.UUID
    tool_name: str = Field(min_length=1, max_length=255)
    action: ToolPolicyAction = "allow"
    risk_score: int = Field(default=0, ge=0, le=100)
    reason: str = Field(default="", max_length=512)


class MCPToolPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    server_id: uuid.UUID
    tool_name: str
    action: str
    risk_score: int
    reason: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MCPToolChainEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    security_event_id: uuid.UUID | None = None
    approval_request_id: uuid.UUID | None = None
    source_agent_id: uuid.UUID | None = None
    target_agent_id: uuid.UUID | None = None
    endpoint_id: uuid.UUID | None = None
    mcp_server_id: uuid.UUID | None = None
    mcp_server_name: str
    tool_name: str
    tool_risk: str
    data_source: str
    external_service: str
    decision: str
    chain_risk_score: int
    risk_band: str = "low"
    policy_id: str | None = None
    policy_name: str
    metadata_json: dict | None = None
    created_at: datetime | None = None


class MCPToolChainSummaryResponse(BaseModel):
    total: int
    allowed: int
    blocked: int
    approval: int
    high_risk: int
    by_decision: dict[str, int]
    by_tool_risk: dict[str, int]
    by_external_service: dict[str, int]


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    risk_score: int
    color: str


class GraphEdge(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: str
    risk_score: int


class MCPToolChainGraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

class MCPPortalServerResponse(BaseModel):
    id: str
    name: str
    category: str
    status: str
    transport: str = "sse"
    endpoint_url: str | None = None
    tools_count: int = 0
    tool_names: list[str] = Field(default_factory=list)
    description: str = ""
    features: list[str] = Field(default_factory=list)
    requires_approval: bool = True
    server_config: dict | None = None

class MCPPortalCatalogResponse(BaseModel):
    servers: list[MCPPortalServerResponse] = Field(default_factory=list)

class MCPPortalRequestStatusResponse(BaseModel):
    status: str
    api_key: str | None = None
    mcp_config: dict | None = None
