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
    helixguard_module: str | None = None


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


class DashboardOverviewResponse(BaseModel):
    metrics: DashboardMetricsResponse
    traffic: list[DashboardTrafficPoint]
    risk_distribution: list[DashboardRiskSlice]
    top_threats: list[DashboardThreatItem]
    llm_usage: list[DashboardLlmUsageItem]
    mcp_activity: list[DashboardMcpActivityRow]
    top_policies: list[DashboardTopPolicyRow]
    top_agents: list[DashboardTopAgentRow]
    compliance_frameworks: list[DashboardComplianceFramework]
    security_trends: list[DashboardSecurityTrendPoint]
