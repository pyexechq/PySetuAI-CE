from typing import Literal

from pydantic import BaseModel, Field


class RagMovementRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32000)
    destination: Literal["pinecone", "vector_store", "embedding"] = "vector_store"
    operation: Literal["upsert", "query", "embed"] = "upsert"
    policy_bundle: str | None = None
    region: str = "US"
    exemption_id: str | None = None


class RagMovementViolation(BaseModel):
    rule: str
    message: str
    severity: str


class RagMovementResponse(BaseModel):
    allowed: bool
    classifications: list[str]
    sensitivity_labels: list[str]
    highest_sensitivity: str | None
    movement: dict[str, str]
    violations: list[RagMovementViolation] = Field(default_factory=list)
    evidence_bundle_id: str | None = None
    stub_note: str | None = None
    exemption_applied: bool = False
    exemption_error: str | None = None


class RagUpsertRequest(RagMovementRequest):
    namespace: str | None = None
    document_id: str | None = None


class RagUpsertResponse(RagMovementResponse):
    upserted: bool = False
    vector_id: str | None = None


class RagPipelineHopResponse(BaseModel):
    hop: str
    movement_from: str
    movement_to: str
    operation: str
    allowed: bool
    blocked_locally: bool = False


class RagIngestRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32000)
    destination: Literal["pinecone", "vector_store"] = "pinecone"
    policy_bundle: str | None = None
    region: str = "US"
    namespace: str | None = None
    document_id: str | None = None
    exemption_id: str | None = None


class RagIngestResponse(BaseModel):
    allowed: bool
    blocked_hop: str | None = None
    hops: list[RagPipelineHopResponse] = Field(default_factory=list)
    classifications: list[str] = Field(default_factory=list)
    sensitivity_labels: list[str] = Field(default_factory=list)
    highest_sensitivity: str | None = None
    vector_id: str | None = None
    upserted: bool = False
    embedding_source: str | None = None
    evidence_bundle_id: str | None = None
    note: str | None = None
    exemption_applied: bool = False
    exemption_error: str | None = None


class GenaiEvidenceSummary(BaseModel):
    id: str
    created_at: str
    actor: str
    bundle_type: str
    allowed: bool
    highest_sensitivity: str | None
    destination: str | None = None
    blocked_hop: str | None = None


class PolicyExemptionCreateRequest(BaseModel):
    reason: str = Field(min_length=8, max_length=2000)
    ticket_ref: str | None = Field(default=None, max_length=128)
    duration_minutes: int = Field(default=60, ge=5, le=1440)
    max_uses: int | None = Field(default=1, ge=1, le=100)
    allowed_destinations: list[Literal["llm", "embedding"]] | None = None


class PolicyExemptionResponse(BaseModel):
    id: str
    created_by: str
    reason: str
    ticket_ref: str | None
    allowed_destinations: list[str]
    expires_at: str
    revoked_at: str | None
    use_count: int
    max_uses: int | None
    created_at: str
    status: str
