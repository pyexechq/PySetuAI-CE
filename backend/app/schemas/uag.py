from pydantic import BaseModel, Field


class UagModelMappingResponse(BaseModel):
    id: str
    requested_model: str
    actual_model: str
    target_provider: str
    emulate_protocol: str
    enabled: bool


class UagModelMappingCreateRequest(BaseModel):
    requested_model: str = Field(..., min_length=1, max_length=128)
    actual_model: str = Field(..., min_length=1, max_length=128)
    target_provider: str = Field(default="openai", max_length=64)
    emulate_protocol: str = Field(default="openai", max_length=64)
    enabled: bool = True


class UagModelMappingUpdateRequest(BaseModel):
    requested_model: str | None = Field(default=None, max_length=128)
    actual_model: str | None = Field(default=None, max_length=128)
    target_provider: str | None = Field(default=None, max_length=64)
    emulate_protocol: str | None = Field(default=None, max_length=64)
    enabled: bool | None = None


class UagTranslationPolicyResponse(BaseModel):
    id: str
    name: str
    conditions: dict
    actions: dict
    priority: int
    enabled: bool


class UagTranslationPolicyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    conditions: dict = Field(default_factory=dict)
    actions: dict = Field(default_factory=dict)
    priority: int = 100
    enabled: bool = True


class UagTranslationPolicyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    conditions: dict | None = None
    actions: dict | None = None
    priority: int | None = None
    enabled: bool | None = None


class UagStatsResponse(BaseModel):
    total_translations: int
    success_rate: float
    failed_translations: int
    avg_latency_ms: float
    compatibility_scores: dict[str, float]
    route_breakdown: dict[str, int]


class UagSettingsResponse(BaseModel):
    client_response_protocol: str = "openai"


class UagSettingsUpdateRequest(BaseModel):
    client_response_protocol: str | None = Field(default=None, max_length=32)


class UagSimulateRequest(BaseModel):
    model: str = "gpt-4o"
    messages: list[dict]
    routing_context: dict | None = None


class UagSimulateResponse(BaseModel):
    original_request: dict
    canonical: dict
    translated_request: dict
    trace: dict
