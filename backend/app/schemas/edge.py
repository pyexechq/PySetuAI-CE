"""Pydantic schemas for Distributed Edge Gateway and Bundle Sync."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EdgeNodeCreate(BaseModel):
    name: str = Field(..., max_length=128)
    region: str = Field(..., max_length=64, description="e.g. us-east-1, eu-central-1, ap-northeast-1, on-prem")
    cloud_provider: str = Field(default="aws", max_length=64)
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    tenant_id: Optional[str] = None


class EdgeNodeResponse(BaseModel):
    id: str
    node_id: str
    name: str
    region: str
    cloud_provider: str
    status: str
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    bundle_version: int
    last_heartbeat_at: Optional[datetime] = None
    sync_latency_ms: float
    requests_routed_24h: int
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    is_active: bool
    created_at: datetime
    enrollment_token: Optional[str] = None  # Returned once on creation


class EdgeNodeListResponse(BaseModel):
    nodes: List[EdgeNodeResponse]
    total_active_nodes: int
    global_sync_healthy: bool
    average_edge_latency_ms: float


class EdgeHeartbeatRequest(BaseModel):
    node_id: str
    bundle_version: int
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    requests_routed_delta: int = 0
    measured_sync_latency_ms: Optional[float] = None


class EdgeHeartbeatResponse(BaseModel):
    status: str
    latest_bundle_version: int
    update_required: bool
    server_time: datetime


class EdgeTelemetryEvent(BaseModel):
    tenant_id: Optional[str] = None
    client_key_hash: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    status_code: int
    dlp_violations: List[str] = []
    anomaly_flagged: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EdgeTelemetryBatchRequest(BaseModel):
    node_id: str
    batch_id: str
    events: List[EdgeTelemetryEvent]


class EdgeTelemetryBatchResponse(BaseModel):
    status: str
    events_ingested: int
    acknowledged_at: datetime


class EdgeSyncBundleResponse(BaseModel):
    bundle_version: int
    generated_at: datetime
    region: str
    client_api_keys: List[Dict[str, Any]]
    policy_rules: List[Dict[str, Any]]
    model_aliases: Dict[str, str]
    dlp_patterns: List[Dict[str, Any]]
    classifier_rules: List[Dict[str, Any]] = Field(default_factory=list)
    mcp_attack_chains: List[Dict[str, Any]] = Field(default_factory=list)
    cost_arbitrage_targets: Dict[str, str] = Field(default_factory=dict)
