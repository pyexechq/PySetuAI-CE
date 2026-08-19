"""Request/response contracts for advanced agentic security (Phase 5)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AnomalyType = Literal["unusual_tool_usage", "unusual_data_access", "unusual_volume", "unusual_timing", "unusual_chain_risk"]
ExfilType = Literal["large_read", "rapid_read", "sensitive_boundary_exit"]
ScanTargetType = Literal["file", "repo", "mcp_resource", "prompt"]


class AgentAnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    endpoint_id: uuid.UUID | None = None
    anomaly_type: str
    severity: str
    risk_score: int
    risk_band: str = "low"
    baseline_value: dict | None = None
    observed_value: dict | None = None
    description: str
    status: str
    source_event_ids: list | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None


class AgentAnomalySummary(BaseModel):
    total: int
    open: int
    high_risk: int
    by_type: dict[str, int]
    by_severity: dict[str, int]


class PromptInjectionFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    endpoint_id: uuid.UUID | None = None
    scan_target_type: str
    scan_target: str
    content_preview: str
    highest_severity: str
    detected: bool
    recommended_action: str
    matches: list | None = None
    status: str
    created_at: datetime | None = None


class PromptInjectionScanRequest(BaseModel):
    content: str = Field(min_length=1)
    target_type: ScanTargetType = "prompt"
    target: str = Field(default="", max_length=1024)


class PromptInjectionScanResponse(BaseModel):
    detected: bool
    highest_severity: str
    recommended_action: str
    matches: list[dict[str, Any]] = Field(default_factory=list)


class PromptInjectionFindingSummary(BaseModel):
    total: int
    open: int
    by_severity: dict[str, int]
    by_target_type: dict[str, int]


class ExfiltrationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    endpoint_id: uuid.UUID | None = None
    exfil_type: str
    resource: str
    tool: str
    bytes_read: int
    event_count: int
    window_seconds: int
    sensitivity: str
    risk_score: int
    risk_band: str = "low"
    status: str
    source_event_ids: list | None = None
    created_at: datetime | None = None


class ExfiltrationEventSummary(BaseModel):
    total: int
    open: int
    high_risk: int
    by_type: dict[str, int]


class GuardianActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_id: uuid.UUID | None = None
    endpoint_id: uuid.UUID | None = None
    trigger_type: str
    trigger_id: uuid.UUID | None = None
    action_type: str
    action_status: str
    policy_id: str | None = None
    policy_name: str
    severity: str
    details: str
    execution_result: dict | None = None
    created_at: datetime | None = None
    executed_at: datetime | None = None


class GuardianSummary(BaseModel):
    total: int
    pending: int
    executed: int
    failed: int
    by_action_type: dict[str, int]


class GuardianRunResponse(BaseModel):
    evaluated: int
    executed: int
    failed: int
