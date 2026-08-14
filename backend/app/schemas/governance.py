from pydantic import BaseModel, Field


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


class McpSsoInjectionConfigRequest(BaseModel):
    enabled: bool = False
    header_name: str = Field(default="Authorization", min_length=1, max_length=128)
    header_format: str = Field(default="Bearer {token}", min_length=1, max_length=256)
    claim_extract: str = Field(default="", max_length=128)


class McpSsoInjectionConfigResponse(McpSsoInjectionConfigRequest):
    server_id: str
    updated_at: str


class McpToolDenyRuleRequest(BaseModel):
    role: str = Field(min_length=1, max_length=50)
    server_id: str
    tool_name: str = Field(min_length=1, max_length=255)
    reason: str = Field(default="Explicit deny by admin", max_length=512)


class McpToolDenyRuleResponse(McpToolDenyRuleRequest):
    id: str
    server_name: str
    created_at: str


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


class DynamicToolSettingsResponse(BaseModel):
    enabled: bool = False
    max_tools: int = 8
    catalog_count: int = 0
    catalog_tokens: int = 0


class DynamicToolSettingsUpdate(BaseModel):
    enabled: bool | None = None
    max_tools: int | None = None


class DynamicToolPreviewRequest(BaseModel):
    query: str
    max_tools: int | None = None


class DynamicToolPreviewResponse(BaseModel):
    enabled: bool
    catalog_count: int
    selected_count: int
    selected_names: list[str]
    original_tokens: int
    compressed_tokens: int
    tokens_saved: int
    savings_pct: float


class McpMultiplexInfoResponse(BaseModel):
    url: str
    api_url: str
    auth: str
    tool_namespace: str
    server_count: int
    tool_count: int
    sample_tools: list[str]
    instructions: str


class McpCatalogEntryResponse(BaseModel):
    slug: str
    name: str
    description: str
    category: str
    transport: str
    default_endpoint: str | None = None
    tool_names: list[str] = []
    auth_required: bool = False
    vendor: str = ""
    installed: bool = False


class McpCatalogListResponse(BaseModel):
    entries: list[McpCatalogEntryResponse]


class McpCatalogInstallRequest(BaseModel):
    endpoint_url: str | None = None
    name: str | None = None


class McpCatalogCustomInstallRequest(BaseModel):
    name: str
    endpoint_url: str
    transport: str = "sse"
    category: str = "Custom"


class McpOAuthStatusResponse(BaseModel):
    configured: bool = False
    enabled: bool = False
    grant_type: str = "client_credentials"
    token_url: str = ""
    client_id: str = ""
    scopes: str = ""
    has_client_secret: bool = False
    has_refresh_token: bool = False
    has_access_token: bool = False
    token_expires_at: str | None = None
    token_fresh: bool = False
    secrets_backend: str = "database"


class McpOAuthServerStatusResponse(McpOAuthStatusResponse):
    server_id: str
    server_name: str


class McpOAuthListResponse(BaseModel):
    servers: list[McpOAuthServerStatusResponse]
    secrets_backend: str = "database"


class McpOAuthUpsertRequest(BaseModel):
    enabled: bool | None = True
    grant_type: str = "client_credentials"
    token_url: str | None = None
    client_id: str | None = None
    scopes: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    access_token: str | None = None


class McpToolRiskItem(BaseModel):
    server_id: str
    server_name: str
    name: str
    description: str = ""
    risk: str
    hidden: bool = False
    auto_hidden: bool = False
    visible: bool = True


class McpToolRiskInventoryResponse(BaseModel):
    auto_hide_destructive: bool = False
    tools: list[McpToolRiskItem]
    visible_count: int = 0
    hidden_count: int = 0


class McpToolRiskSettingsUpdate(BaseModel):
    auto_hide_destructive: bool


class McpToolRiskOverride(BaseModel):
    name: str
    risk: str | None = None
    hidden: bool | None = None


class McpToolRiskUpdateRequest(BaseModel):
    tools: list[McpToolRiskOverride]


class McpAgentItem(BaseModel):
    slug: str
    label: str
    enabled: bool


class McpAgentServerAccess(BaseModel):
    server_id: str
    server_name: str
    allowed_agents: list[str] = []


class McpAgentSettingsResponse(BaseModel):
    agents: list[McpAgentItem]
    servers: list[McpAgentServerAccess]


class McpAgentSettingsUpdate(BaseModel):
    toggles: dict[str, bool]


class McpAgentServerAccessUpdate(BaseModel):
    allowed_agents: list[str] = []


class McpAgentDetectRequest(BaseModel):
    user_agent: str | None = None
    metadata: dict | None = None


class McpAgentDetectResponse(BaseModel):
    agent: str
    mcp_enabled: bool
    label: str


class McpPortalEntry(BaseModel):
    server_id: str
    name: str
    category: str
    status: str
    tool_count: int
    tool_names: list[str] = []
    auth_required: bool
    connection_status: str
    catalog_slug: str | None = None
    vendor: str = ""
    description: str = ""
    portal_visible: bool = True


class McpPortalListResponse(BaseModel):
    enabled: bool
    multiplex_url: str
    entries: list[McpPortalEntry]


class McpPortalSettingsResponse(BaseModel):
    enabled: bool


class McpPortalSettingsUpdate(BaseModel):
    enabled: bool


class McpPortalVisibilityUpdate(BaseModel):
    portal_visible: bool


class McpPortalConnectRequest(BaseModel):
    access_token: str


class McpPortalConnectResponse(BaseModel):
    server_id: str
    connection_status: str
    connected_at: str


class McpUrlFilterSettingsResponse(BaseModel):
    enabled: bool
    mode: str
    patterns: list[str]
    block_private_ips: bool
    web_search_enabled: bool
    vendor: str
    vendor_endpoint: str
    vendor_configured: bool = False


class McpUrlFilterSettingsUpdate(BaseModel):
    enabled: bool | None = None
    mode: str | None = None
    patterns: list[str] | None = None
    block_private_ips: bool | None = None
    web_search_enabled: bool | None = None
    vendor: str | None = None
    vendor_endpoint: str | None = None
    vendor_api_key: str | None = None


class McpUrlFilterProbeRequest(BaseModel):
    url: str


class McpUrlFilterProbeResponse(BaseModel):
    url: str
    host: str
    allowed: bool
    mode: str
    private_host: bool


class McpSpecTool(BaseModel):
    name: str
    description: str
    method: str | None = None
    path: str | None = None
    tags: list[str] = []


class McpSpecParseRequest(BaseModel):
    protocol: str
    spec_url: str | None = None
    spec_text: str | None = None


class McpSpecParseResponse(BaseModel):
    protocol: str
    tools: list[McpSpecTool]
    endpoint_url: str = ""


class PolicyRuleUpdateRequest(BaseModel):
    id: str
    name: str
    condition: str
    action: str
    severity: str
    enabled: bool = True


class PolicyRulesSaveRequest(BaseModel):
    rules: list[PolicyRuleUpdateRequest]


class PolicyTestRequest(BaseModel):
    content: str
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
    has_request_log: bool = False
    matched_routing_rule: str | None = None
    routing_strategy: str | None = None
    upstream: str | None = None


class AuditLogBodyResponse(BaseModel):
    audit_log_id: str
    request_payload: dict | None = None
    response_payload: dict | None = None
    guardrail_events: dict | None = None
    tool_events: list[dict] | None = None
    created_at: str | None = None


class RequestLogSettingsResponse(BaseModel):
    retention_days: int
    stored_entries: int


class RequestLogSettingsUpdateRequest(BaseModel):
    retention_days: int = Field(ge=1, le=365)


class RequestLogPurgeResponse(BaseModel):
    purged: int
    stored_entries: int


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
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0
    model_aliases: list[str] = Field(default_factory=list)


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
    model_aliases: list[str] | None = None
    cost_per_1m_input: float | None = Field(default=None, ge=0)
    cost_per_1m_output: float | None = Field(default=None, ge=0)


class LLMProviderUpdateRequest(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    endpoint_url: str | None = None
    is_active: bool | None = None
    percentage: float | None = None
    api_key: str | None = None
    model_aliases: list[str] | None = None
    cost_per_1m_input: float | None = Field(default=None, ge=0)
    cost_per_1m_output: float | None = Field(default=None, ge=0)


class RoutingRuleResponse(BaseModel):
    id: str
    name: str
    priority: int
    condition: str
    target_model: str
    status: str
    response_format: str
    target_provider: str | None = None


class RoutingRuleCreateRequest(BaseModel):
    name: str
    priority: int = 10
    condition: str
    target_model: str
    status: str = "draft"
    response_format: str = "auto"
    target_provider: str | None = None


class RoutingRuleUpdateRequest(BaseModel):
    name: str | None = None
    priority: int | None = None
    condition: str | None = None
    target_model: str | None = None
    status: str | None = None
    response_format: str | None = None
    target_provider: str | None = None


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
    stage: str = ""
    offset_ms: int = 0
    detail: str | None = None
    attributes: dict | None = None


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
    otel_trace_id: str | None = None
    audit_id: str | None = None
