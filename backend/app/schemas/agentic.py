"""Request/response contracts for the endpoint and agent control plane."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AgentDecision = Literal["allowed", "blocked", "redacted", "approval", "log"]


class EndpointRegisterRequest(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    os_name: str = Field(default="", max_length=64)
    os_version: str = Field(default="", max_length=128)
    agent_version: str = Field(default="", max_length=64)
    metadata: dict = Field(default_factory=dict)


class EndpointHeartbeatRequest(BaseModel):
    status: Literal["online", "offline", "degraded"] = "online"
    agent_version: str | None = Field(default=None, max_length=64)


class EndpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    hostname: str
    os_name: str
    os_version: str
    agent_version: str
    status: str
    last_seen_at: datetime | None = None
    registered_at: datetime | None = None
    metadata_json: dict | None = None


class AgentRegisterRequest(BaseModel):
    endpoint_id: str | None = None
    name: str = Field(min_length=1, max_length=255)
    agent_type: str = Field(min_length=1, max_length=64)
    vendor: str = Field(default="", max_length=128)
    version: str = Field(default="", max_length=64)
    user_name: str = Field(default="", max_length=255)
    status: str = Field(default="active", max_length=32)
    data_sources: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    mcp_servers: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    endpoint_id: uuid.UUID | None = None
    name: str
    agent_type: str
    vendor: str
    version: str
    user_name: str
    status: str
    risk_score: int
    data_sources: list | None = None
    tools: list | None = None
    mcp_servers: list | None = None
    permissions: list | None = None
    last_activity_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SecurityEventIngestRequest(BaseModel):
    endpoint_id: str | None = None
    agent_id: str | None = None
    source: str = Field(default="endpoint", max_length=64)
    event_type: str = Field(default="agent", max_length=64)
    user_name: str = Field(default="", max_length=255)
    tool: str = Field(default="", max_length=255)
    action: str = Field(min_length=1, max_length=128)
    resource: str = Field(default="", max_length=1024)
    classification: list[str] = Field(default_factory=list)
    decision: AgentDecision = "log"
    risk_score: int = Field(default=0, ge=0, le=100)
    policy_id: str | None = Field(default=None, max_length=64)
    policy_name: str = Field(default="", max_length=255)
    metadata: dict = Field(default_factory=dict)


class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    endpoint_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    audit_log_id: uuid.UUID | None = None
    source: str
    event_type: str
    user_name: str
    tool: str
    action: str
    resource: str
    classification: list | None = None
    decision: str
    risk_score: int
    policy_id: str | None = None
    policy_name: str
    metadata_json: dict | None = None
    created_at: datetime | None = None


class SecurityEventIngestResponse(BaseModel):
    event_id: str
    audit_log_id: str


class SecurityEventSummary(BaseModel):
    total: int
    blocked: int
    redacted: int
    allowed: int
    high_risk: int
    by_decision: dict[str, int]
    by_type: dict[str, int]


class ApprovalDecisionRequest(BaseModel):
    reason: str = Field(default="", max_length=512)


class FileGovernanceRule(BaseModel):
    pattern: str
    classification: str = "*"
    action: str = "allow"


class AgentPolicyResponse(BaseModel):
    version: str = "1"
    rules: list[FileGovernanceRule] = Field(default_factory=list)


class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    security_event_id: uuid.UUID | None = None
    endpoint_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    user_name: str
    tool: str
    action: str
    resource: str
    classification: list | None = None
    risk_score: int
    reason: str
    policy_id: str | None = None
    policy_name: str
    status: str
    decided_by: str
    decided_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None
