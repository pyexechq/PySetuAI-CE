from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o"
    messages: list[ChatMessage]
    temperature: float | None = 0.7
    max_tokens: int | None = None
    stream: bool = False
    routing_context: dict | None = None
    user: str | None = None
    metadata: dict | None = None
    tools: list[dict] | None = None


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage
    pysetu: dict | None = None


class OpenAIError(BaseModel):
    message: str
    type: str = "invalid_request_error"
    code: str | None = None


class OpenAIErrorResponse(BaseModel):
    error: OpenAIError


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 1686935002
    owned_by: str = "pysetu"


class ModelsListResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


class PolicyViolation(BaseModel):
    rule_name: str
    action: str
    severity: str
    detail: str


class InspectionResult(BaseModel):
    allowed: bool
    action: str = "allow"
    violations: list[PolicyViolation] = Field(default_factory=list)
    redacted_content: str | None = None
    risk: str = "low"
