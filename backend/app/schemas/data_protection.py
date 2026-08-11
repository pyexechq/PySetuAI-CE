from pydantic import BaseModel


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
