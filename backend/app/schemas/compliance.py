from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.dashboard import DashboardComplianceFramework


class ComplianceSnapshotCreateRequest(BaseModel):
    notes: str = Field(default="", max_length=2000)


class ComplianceSnapshotSummary(BaseModel):
    id: str
    created_at: datetime
    created_by_name: str
    period_start: datetime
    period_end: datetime
    overall_score: float
    frameworks_compliant: int
    frameworks_total: int
    notes: str


class ComplianceSnapshotDetail(ComplianceSnapshotSummary):
    frameworks: list[DashboardComplianceFramework]


class ComplianceReevaluateResponse(BaseModel):
    framework: DashboardComplianceFramework
    evaluated_at: datetime


class ComplianceRemediationRequest(BaseModel):
    framework_name: str = Field(..., min_length=1, max_length=128)
    control_id: str = Field(..., min_length=1, max_length=128)
    mode: str = Field(default="manual", pattern="^(manual|ai)$")


class ComplianceRemediationResponse(BaseModel):
    control_id: str
    framework_name: str
    framework_slug: str
    mode: str
    summary: str
    steps: list[str]
    manual_route: str | None = None
    ai_generated: bool = False
    estimated_effort: str | None = None
    generated_at: datetime


class ComplianceFrameworkGapSummary(BaseModel):
    framework_name: str
    framework_slug: str
    gaps_count: int
    not_met: int
    in_progress: int
    priority_controls: list[dict[str, str | None]]
