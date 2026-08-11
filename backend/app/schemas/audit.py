from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AuditIngestEventRequest(BaseModel):
    actor: str = Field(..., min_length=1, max_length=255)
    action: str = Field(..., min_length=1, max_length=100)
    resource: str = Field(..., min_length=1, max_length=255)
    status: str = Field(..., pattern="^(?i)(allowed|blocked|review)$")
    risk: str = Field(default="low", pattern="^(?i)(low|medium|high|critical)$")
    details: str = ""
    timestamp: datetime | None = None
    source: str = Field(default="external", max_length=64)
    external_id: str | None = Field(default=None, max_length=255)
    trace_id: str | None = Field(default=None, max_length=128)

    @field_validator("status", "risk", mode="before")
    @classmethod
    def _lower_enum(cls, value: str) -> str:
        return str(value).strip().lower()


class AuditIngestRequest(BaseModel):
    events: list[AuditIngestEventRequest] = Field(..., min_length=1)


class AuditIngestResponse(BaseModel):
    accepted: int
    skipped: int
    duplicates: int
    ids: list[str]


class AuditIngestBatchResponse(BaseModel):
    job_id: str
    queued: int
    message: str


class AuditIngestJobStatusResponse(BaseModel):
    job_id: str
    state: str
    result: AuditIngestResponse | None = None
    error: str | None = None


class AuditIngestSourceStat(BaseModel):
    source: str
    count: int


class SiemConnectorCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    connector_type: str = Field(default="webhook", max_length=32)
    endpoint_url: str = Field(..., min_length=1, max_length=1024)
    auth_token: str | None = Field(default=None, max_length=4096)
    export_format: str = Field(default="json", max_length=16)
    enabled: bool = True


class SiemConnectorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    connector_type: str | None = Field(default=None, max_length=32)
    endpoint_url: str | None = Field(default=None, min_length=1, max_length=1024)
    auth_token: str | None = Field(default=None, max_length=4096)
    export_format: str | None = Field(default=None, max_length=16)
    enabled: bool | None = None


class SiemConnectorResponse(BaseModel):
    id: str
    name: str
    connector_type: str
    endpoint_url: str
    export_format: str
    enabled: bool
    events_exported: int
    last_export_at: str | None = None
    last_error: str = ""
    auth_token_set: bool = False
    auth_token_masked: str | None = None


class SiemExportResponse(BaseModel):
    exported: int
    connector_id: str
    connector_name: str
    message: str
