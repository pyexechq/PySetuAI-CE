from datetime import datetime

from pydantic import BaseModel, Field


class QATestCycleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    import_baseline: bool = False
    import_baseline_defects: bool = False


class QATestCycleUpdateRequest(BaseModel):
    status: str | None = None
    release_decision: str | None = None
    notes: str | None = None


class QATestCaseUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(not_tested|pass|fail|blocked|skipped)$")
    notes: str | None = None


class QADefectCreateRequest(BaseModel):
    defect_code: str = Field(..., min_length=1, max_length=32)
    severity: str = Field(..., pattern="^(S1|S2|S3|S4)$")
    module: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=512)
    description: str = ""
    cycle_id: str | None = None
    linked_case_id: str | None = None


class QADefectUpdateRequest(BaseModel):
    severity: str | None = Field(default=None, pattern="^(S1|S2|S3|S4)$")
    title: str | None = Field(default=None, max_length=512)
    description: str | None = None
    status: str | None = Field(default=None, pattern="^(open|fixed|wont_fix|deferred)$")


class QATestCaseResponse(BaseModel):
    id: str
    cycle_id: str
    case_id: str
    module: str
    title: str
    priority: str
    method: str
    status: str
    notes: str
    automated_key: str | None
    tested_by_name: str
    tested_at: datetime | None
    remediation_hint: str | None = None
    linked_defect_code: str | None = None
    suggested_severity: str | None = None


class QADefectResponse(BaseModel):
    id: str
    cycle_id: str | None
    linked_case_id: str | None
    linked_case_code: str | None
    defect_code: str
    severity: str
    module: str
    title: str
    description: str
    status: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime


class QATestCycleSummary(BaseModel):
    id: str
    name: str
    status: str
    release_decision: str
    notes: str
    started_at: datetime | None
    completed_at: datetime | None
    created_by_name: str
    created_at: datetime
    total_cases: int
    passed_cases: int
    failed_cases: int
    blocked_cases: int
    not_tested_cases: int


class QATestCycleDetail(QATestCycleSummary):
    cases: list[QATestCaseResponse]


class QAOverviewResponse(BaseModel):
    active_cycle: QATestCycleSummary | None
    total_cycles: int
    total_open_defects: int
    s1_open_defects: int
    s2_open_defects: int
    overall_pass_rate: float
    modules_in_scope: list[str]
    release_decision: str


class QAAutomatedRunResponse(BaseModel):
    pytest_exit_code: int
    tests_run: int
    tests_passed: int
    tests_failed: int
    cases_updated: int
    tests_targeted: int = 0
    scope: str = "all"
    output_tail: str


class QAFileDefectResponse(BaseModel):
    defect: QADefectResponse
    created: bool
