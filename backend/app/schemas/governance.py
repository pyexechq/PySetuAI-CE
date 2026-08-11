from pydantic import BaseModel


class PolicyTreeNode(BaseModel):
    id: str
    label: str
    type: str
    status: str | None = None
    children: list["PolicyTreeNode"] | None = None


class PolicyCreateRequest(BaseModel):
    name: str
    policy_type: str = "policy"
    status: str = "draft"
    parent_id: str | None = None


class PolicyUpdateRequest(BaseModel):
    name: str | None = None
    status: str | None = None


class PolicyRuleResponse(BaseModel):
    id: str
    name: str
    condition: str
    action: str
    severity: str
    enabled: bool


class PolicyGraphLinkResponse(BaseModel):
    policy_id: str
    policy_name: str
    policy_status: str | None
    graph_node_id: str
    graph_node_label: str
    graph_node_type: str
    edge_labels: list[str]
    description: str


class IngressBindingPolicyResponse(BaseModel):
    policy_id: str
    policy_name: str
    policy_status: str | None
    graph_node_id: str
    graph_node_label: str


class IngressBindingResponse(BaseModel):
    id: str
    name: str
    bundle_id: str | None
    bundle_name: str | None
    is_default: bool
    graph_node_ids: list[str]
    policies: list[IngressBindingPolicyResponse]


class MCPServerResponse(BaseModel):
    id: str
    name: str
    category: str
    success_rate: float
    avg_latency: int
    total_calls: int
    status: str
    tools: int
    tool_names: list[str] = []
    endpoint_url: str | None = None
    transport: str = "sse"
    connection_config: dict = {}
    trust_score: float
    risk_score: float


class MCPServerCreateRequest(BaseModel):
    name: str
    category: str
    status: str = "healthy"
    tool_names: list[str] = []
    endpoint_url: str | None = None
    transport: str = "sse"
    connection_config: dict | None = None


class MCPServerUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    status: str | None = None
    tool_names: list[str] | None = None
    endpoint_url: str | None = None
    transport: str | None = None
    connection_config: dict | None = None


class McpHealthCheckResponse(BaseModel):
    server_id: str
    server_name: str
    status: str
    ok: bool
    latency_ms: int
    message: str
    http_status: int | None = None
    skipped: bool = False
    checked_at: str


class McpHealthCheckBatchResponse(BaseModel):
    results: list[McpHealthCheckResponse]
    healthy: int
    degraded: int
    offline: int
    skipped: int


class McpDiscoverToolsResponse(BaseModel):
    server_id: str
    server_name: str
    ok: bool
    tool_names: list[str]
    tools_count: int
    tool_schemas: list[dict] = []
    message: str
    latency_ms: int = 0
    skipped: bool = False
    checked_at: str


class PolicyRuleUpdateRequest(BaseModel):
    id: str
    name: str
    condition: str
    action: str
    severity: str
    enabled: bool = True


class PolicyRulesSaveRequest(BaseModel):
    rules: list[PolicyRuleUpdateRequest]


class PolicyConditionHelpExample(BaseModel):
    title: str
    condition: str
    description: str
    action: str = "Block"
    severity: str = "high"


class PolicyRuleSuggestionResponse(BaseModel):
    id: str
    name: str
    condition: str
    action: str
    severity: str
    enabled: bool = True
    rationale: str


class PolicyAssistRequest(BaseModel):
    goal: str = ""
    policy_name: str | None = None
    existing_rule_names: list[str] = []


class PolicyAssistResponse(BaseModel):
    summary: str
    suggestions: list[PolicyRuleSuggestionResponse]
    condition_help: list[PolicyConditionHelpExample]
    ai_enhanced: bool = False
    ai_assist_available: bool = False


class AuditLogResponse(BaseModel):
    id: str
    timestamp: str
    actor: str
    action: str
    resource: str
    status: str
    risk: str
    details: str


class RoutingModelResponse(BaseModel):
    id: str
    model: str
    provider_type: str
    endpoint_url: str | None = None
    requests: int
    percentage: float
    latency: int
    success_rate: float
    is_active: bool = True
    api_key_set: bool = False
    api_key_masked: str | None = None


class ProviderShareItem(BaseModel):
    id: str
    model: str
    requests: int
    previous_percentage: float
    percentage: float


class ProviderRebalanceResponse(BaseModel):
    total_requests: int
    providers: list[ProviderShareItem]
    message: str


class McpToolInvokeRequest(BaseModel):
    tool_name: str
    arguments: dict = {}


class McpToolInvokeResponse(BaseModel):
    server_id: str
    server_name: str
    ok: bool
    message: str
    result: dict | None = None
    latency_ms: int = 0
    skipped: bool = False
    session_reused: bool = False
    checked_at: str


class LLMProviderCreateRequest(BaseModel):
    name: str
    provider_type: str
    endpoint_url: str | None = None
    is_active: bool = True
    api_key: str | None = None


class LLMProviderUpdateRequest(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    endpoint_url: str | None = None
    is_active: bool | None = None
    percentage: float | None = None
    api_key: str | None = None


class RoutingRuleResponse(BaseModel):
    id: str
    name: str
    priority: int
    condition: str
    target_model: str
    status: str


class RoutingRuleCreateRequest(BaseModel):
    name: str
    priority: int = 10
    condition: str
    target_model: str
    status: str = "draft"


class RoutingRuleUpdateRequest(BaseModel):
    name: str | None = None
    priority: int | None = None
    condition: str | None = None
    target_model: str | None = None
    status: str | None = None


class GatewayStatusResponse(BaseModel):
    status: str
    openai_compatible: bool
    gemini_compatible: bool
    requests_today: int
    blocked_today: int
    endpoints: list[str]
    proxy_mode: str = "mock"
    opa_enabled: bool = False
    opa_available: bool = False


class ObservabilityActionCount(BaseModel):
    action: str
    count: int


class ObservabilityRiskCount(BaseModel):
    risk: str
    count: int


class ObservabilityTrendPoint(BaseModel):
    date: str
    total: int
    blocked: int


class ObservabilityOverviewResponse(BaseModel):
    total_events_today: int
    allowed_today: int
    blocked_today: int
    under_review_today: int
    block_rate: float
    avg_latency_ms: int
    p95_latency_ms: int
    error_rate: float
    by_action: list[ObservabilityActionCount]
    by_risk: list[ObservabilityRiskCount]
    daily_trend: list[ObservabilityTrendPoint]


class TraceSpanResponse(BaseModel):
    name: str
    service: str
    duration_ms: int
    status: str


class TraceSummaryResponse(BaseModel):
    id: str
    trace_id: str
    timestamp: str
    actor: str
    action: str
    resource: str
    status: str
    risk: str
    duration_ms: int
    span_count: int
    spans: list[TraceSpanResponse]
