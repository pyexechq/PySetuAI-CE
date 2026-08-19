"""Request/response contracts for Microsoft Copilot governance (Phase 4)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

InstanceType = Literal["m365_copilot", "copilot_studio_agent", "teams"]
ConnectorType = Literal["power_platform", "graph", "custom"]


class CopilotInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    external_id: str
    instance_type: str
    name: str
    display_name: str
    status: str
    risk_score: int
    risk_band: str = "low"
    owner: str
    environment: str
    data_sources: list | None = None
    permissions: list | None = None
    metadata_json: dict | None = None
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CopilotConnectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    external_id: str
    name: str
    connector_type: str
    publisher: str
    status: str
    risk_score: int
    risk_band: str
    auth_type: str
    scopes: list | None = None
    data_sources: list | None = None
    permissions: list | None = None
    metadata_json: dict | None = None
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CopilotSyncRequest(BaseModel):
    instances: list[dict[str, Any]] = Field(default_factory=list)
    connectors: list[dict[str, Any]] = Field(default_factory=list)
    audit_events: list[dict[str, Any]] = Field(default_factory=list)


class CopilotSyncResponse(BaseModel):
    instances_upserted: int
    instances_removed: int
    connectors_upserted: int
    connectors_removed: int
    drift_found: int


class CopilotDriftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    baseline_id: uuid.UUID | None = None
    entity_type: str
    entity_id: uuid.UUID | None = None
    entity_external_id: str
    entity_name: str
    drift_type: str
    severity: str
    previous_value: dict | None = None
    current_value: dict | None = None
    description: str
    status: str
    created_at: datetime | None = None
    resolved_at: datetime | None = None


class CopilotBaselineCreateRequest(BaseModel):
    name: str = Field(default="", max_length=255)
    created_by: str = Field(default="", max_length=255)


class CopilotBaselineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    created_by: str
    created_at: datetime | None = None


class CopilotSummaryResponse(BaseModel):
    instances_total: int
    instances_by_type: dict[str, int]
    connectors_total: int
    connectors_by_type: dict[str, int]
    high_risk_instances: int
    high_risk_connectors: int
    open_drift: int
    by_severity: dict[str, int]
