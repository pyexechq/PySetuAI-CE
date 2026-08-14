import re

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, field_validator


class ReportKpiResponse(BaseModel):
    label: str
    value: str
    change: str
    trend: str


class CompoundingCostLayer(BaseModel):
    id: str
    label: str
    tokens_saved: int = 0
    estimated_usd: float = 0.0
    requests: int = 0
    share_pct: float = 0.0


class CompoundingCostSummary(BaseModel):
    layers: list[CompoundingCostLayer]
    total_tokens_saved: int = 0
    total_estimated_usd: float = 0.0
    narrative: str = ""


class ReportSchedule(BaseModel):
    enabled: bool = False
    frequency: str = "on_demand"
    time: str = "09:00"
    day_of_week: int | None = None
    day_of_month: int | None = None
    next_run_at: str | None = None
    recipients: list[str] = Field(default_factory=list)

    @field_validator("recipients", mode="before")
    @classmethod
    def normalize_recipients(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = re.split(r"[,;\n]+", value)
            return [part.strip() for part in parts if part.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @field_validator("recipients")
    @classmethod
    def validate_recipient_emails(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for email in value:
            try:
                normalized.append(validate_email(email, check_deliverability=False).normalized)
            except EmailNotValidError as exc:
                raise ValueError(f"Invalid delivery email: {email}") from exc
        return normalized


class ReportQuery(BaseModel):
    source: str = "audit_logs"
    filters: dict = Field(default_factory=dict)
    limit: int = 1000


class ReportCatalogStats(BaseModel):
    row_count: int = 0
    generated_at: str | None = None


class ReportCatalogItem(BaseModel):
    id: str
    report_uuid: str
    name: str
    description: str
    category: str
    frequency: str
    format: str
    last_generated: str
    status: str
    query: ReportQuery
    schedule: ReportSchedule
    is_builtin: bool = False
    stats: ReportCatalogStats = Field(default_factory=ReportCatalogStats)


class ExecutiveSummaryResponse(BaseModel):
    period: str
    kpis: list[ReportKpiResponse]
    compliance_score: float
    frameworks_compliant: int
    frameworks_total: int
    top_risks: list[str]
    cost_optimization: CompoundingCostSummary | None = None


class ReportCatalogResponse(BaseModel):
    reports: list[ReportCatalogItem]


class ReportQueryTemplateField(BaseModel):
    key: str
    label: str
    type: str
    options: list[str] | None = None
    default: int | str | None = None


class ReportQueryTemplate(BaseModel):
    source: str
    label: str
    description: str
    filter_fields: list[ReportQueryTemplateField]


class ReportQueryTemplatesResponse(BaseModel):
    templates: list[ReportQueryTemplate]


class ReportCreateRequest(BaseModel):
    name: str
    description: str = ""
    category: str = "Custom"
    format: str = "CSV"
    query: ReportQuery = Field(default_factory=ReportQuery)
    schedule: ReportSchedule | None = None


class ReportUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    format: str | None = None
    query: ReportQuery | None = None
    schedule: ReportSchedule | None = None


class ReportRunResponse(BaseModel):
    report_id: str
    columns: list[str]
    rows: list[list]
    row_count: int
    generated_at: str


class ReportPreviewRequest(BaseModel):
    query: ReportQuery


class ReportPreviewResponse(BaseModel):
    columns: list[str]
    rows: list[list]
    row_count: int


class ReportDeliveryRecipient(BaseModel):
    email: str
    name: str
    role: str


class ReportDeliveryRecipientsResponse(BaseModel):
    recipients: list[ReportDeliveryRecipient]


class ReportSchedulerStatus(BaseModel):
    celery_broker: str
    smtp_enabled: bool
    smtp_host: str
    due_reports: int
    mailhog_ui: str | None = None
