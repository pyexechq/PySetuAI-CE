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
