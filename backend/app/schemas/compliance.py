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
    module_name: str | None = None
    evidence: str | None = None
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


class IacEvidenceCheckConfig(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=255)
    framework: str = Field(default="", max_length=128)
    pattern: str = Field(..., min_length=1, max_length=255)
    enabled: bool = True


class IacEvidenceConfigDefaults(BaseModel):
    scan_paths: list[str]
    checks: list[IacEvidenceCheckConfig]


class IacEvidenceConfigResponse(BaseModel):
    deploy_root: str
    deploy_root_env: str
    scan_paths: list[str]
    checks: list[IacEvidenceCheckConfig]
    is_customized: bool
    defaults: IacEvidenceConfigDefaults


class IacEvidenceConfigUpdateRequest(BaseModel):
    scan_paths: list[str] = Field(..., min_length=1)
    checks: list[IacEvidenceCheckConfig] = Field(..., min_length=1)


class IacEvidenceCheckResult(BaseModel):
    id: str
    title: str
    framework: str
    status: str
    evidence_files: list[str]
    detail: str


class IacEvidenceScanResponse(BaseModel):
    id: str
    generated_at: str
    scanner: str
    deploy_root: str
    scan_paths: list[str]
    files_scanned: int
    score: float
    summary: dict[str, int]
    checks: list[IacEvidenceCheckResult]


class DataMovementPolicy(BaseModel):
    restricted_labels: list[str] = Field(..., min_length=1)
    vector_destinations: list[str] = Field(..., min_length=1)
    never_exempt_labels: list[str] = Field(default_factory=list)


class DataMovementPolicyOption(BaseModel):
    id: str
    label: str


class DataMovementPolicyResponse(BaseModel):
    policy: DataMovementPolicy
    is_customized: bool
    defaults: DataMovementPolicy
    label_options: list[DataMovementPolicyOption]
    destination_options: list[DataMovementPolicyOption]
    opa_policy_path: str


class DataMovementPolicyUpdateRequest(BaseModel):
    policy: DataMovementPolicy
