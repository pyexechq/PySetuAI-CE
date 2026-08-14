from pydantic import BaseModel, Field


class DlpScanRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32000)


class DlpScanResponse(BaseModel):
    classifications: list[str]
    sensitivity_labels: list[str] = Field(default_factory=list)
    highest_sensitivity: str | None = None
    has_pii: bool
    region: str
    match_count: int
    redacted_content: str | None


class DataClassificationItem(BaseModel):
    label: str
    count: int
    percentage: float
    color: str


class DataResidencyRegionItem(BaseModel):
    id: str
    name: str
    percentage: float
    records: int
    status: str
    color: str
    hubs: list[str]
    policy: str


class DataProtectionOverviewResponse(BaseModel):
    classifications: list[DataClassificationItem]
    regions: list[DataResidencyRegionItem]
    total_scanned: int
    pii_redactions: int
    blocked_events: int
