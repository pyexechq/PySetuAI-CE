"""Request/response contracts for the browser-extension API surface."""

from pydantic import BaseModel, Field


class ExtensionConfigResponse(BaseModel):
    bundle_id: str | None = None
    target_domains: list[str] = Field(default_factory=list)


class ExtensionScanRequest(BaseModel):
    content: str
    site: str | None = None
    url: str | None = None


class ExtensionScanResponse(BaseModel):
    allowed: bool
    action: str = "allow"
    matched_rule: str | None = None
    sensitivity_labels: list[str] = Field(default_factory=list)
    reason: str = ""
    redacted_content: str | None = None
    input_hash: str | None = None
    input_length: int = 0


class ExtensionIncidentRequest(BaseModel):
    site: str
    url: str
    action: str
    matched_rule: str | None = None
    sensitivity_labels: list[str] = Field(default_factory=list)
    snippet_hash: str | None = None
    redacted_input: str | None = Field(default=None, max_length=65536)
    input_hash: str | None = Field(default=None, min_length=64, max_length=64)
    input_length: int = Field(default=0, ge=0)
