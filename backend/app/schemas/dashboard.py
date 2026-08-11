from datetime import datetime

from pydantic import BaseModel

from app.schemas.auth import DashboardMetricsResponse


class DashboardTrafficPoint(BaseModel):
    date: str
    total_requests: int
    blocked_requests: int


class DashboardRiskSlice(BaseModel):
    level: str
    count: int
    percentage: float


class DashboardThreatItem(BaseModel):
    name: str
    count: int


class DashboardLlmUsageItem(BaseModel):
    model: str
    percentage: float
    requests: int
    total_tokens: int = 0
    avg_tokens_per_request: float = 0.0
    cost_usd: float = 0.0


class DashboardLlmUsageSummary(BaseModel):
    total_tokens: int = 0
    token_utilization_pct: float = 0.0
    avg_burn_usd_per_day: float = 0.0
    total_cost_usd: float = 0.0
    monthly_token_quota: int = 50_000_000


class DashboardMcpActivityRow(BaseModel):
    server: str
    total_calls: int
    blocked: int
    risk: str


class DashboardTopPolicyRow(BaseModel):
    rank: int
    name: str
    requests: int
    violations: int
    enforcement: str


class DashboardTopAgentRow(BaseModel):
    rank: int
    name: str
    requests: int
    success_rate: float
    avg_latency: float


class DashboardComplianceControl(BaseModel):
    id: str
    title: str
    requirement: str
    status: str
    evidence: str | None = None
    remediation: str | None = None
    pysetu_module: str | None = None


class DashboardComplianceFramework(BaseModel):
    name: str
    score: float
    status: str
    controls: int
    passed: int
    in_progress: int = 0
    not_met: int = 0
    control_items: list[DashboardComplianceControl] = []


class DashboardSecurityTrendPoint(BaseModel):
    date: str
    blocked: int
    allowed: int
    under_review: int


class DashboardUagRouteItem(BaseModel):
    route: str
    count: int


class DashboardUagMetrics(BaseModel):
    protocol_translations: int
    provider_migrations: int
    cost_savings_usd: float
    legacy_app_compatibility: float
    route_breakdown: list[DashboardUagRouteItem] = []


class DashboardMetricInsightResponse(BaseModel):
    metric_key: str
    title: str
    summary: str
    insights: list[str]
    recommended_actions: list[str]
    ai_generated: bool = False
    generated_at: datetime


class DashboardOverviewResponse(BaseModel):
    metrics: DashboardMetricsResponse
    traffic: list[DashboardTrafficPoint]
    risk_distribution: list[DashboardRiskSlice]
    top_threats: list[DashboardThreatItem]
    llm_usage: list[DashboardLlmUsageItem]
    llm_usage_summary: DashboardLlmUsageSummary | None = None
    mcp_activity: list[DashboardMcpActivityRow]
    top_policies: list[DashboardTopPolicyRow]
    top_agents: list[DashboardTopAgentRow]
    compliance_frameworks: list[DashboardComplianceFramework]
    security_trends: list[DashboardSecurityTrendPoint]
    uag: DashboardUagMetrics | None = None
