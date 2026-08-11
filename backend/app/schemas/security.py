from pydantic import BaseModel, Field


class SecurityThreatBreakdown(BaseModel):
    category: str
    label: str
    count: int
    percentage: float


class SecurityDetectionItem(BaseModel):
    id: str
    timestamp: str
    category: str
    actor: str
    action: str
    resource: str
    risk: str
    details: str


class SecurityTrendPoint(BaseModel):
    date: str
    prompt_injection: int
    jailbreak: int
    data_exfiltration: int
    secret_leakage: int


class SecurityOverviewResponse(BaseModel):
    threats_blocked_30d: int
    rules_active: int
    breakdown: list[SecurityThreatBreakdown]
    recent_detections: list[SecurityDetectionItem]
    threat_trends: list[SecurityTrendPoint]


class SecurityScanRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32000)


class SecurityScanMatch(BaseModel):
    rule_id: str
    name: str
    category: str
    severity: str
    detail: str


class SecurityScanResponse(BaseModel):
    detected: bool
    recommended_action: str
    highest_severity: str
    matches: list[SecurityScanMatch]


class OpaStatusResponse(BaseModel):
    enabled: bool
    available: bool
    policy_path: str
    fail_open: bool
    base_url: str
    error: str | None = None


class AbacEvaluateRequest(BaseModel):
    role: str = "developer"
    auth_type: str = Field(default="jwt", pattern="^(?i)(jwt|client_key)$")
    actor: str = "demo@acme.com"
    bundle: str = "Standard Support"
    model: str = "auto"
    routed_model: str = "GPT-4o"
    has_pii: bool = False
    region: str = "US"
    risk: str = Field(default="low", pattern="^(?i)(low|medium|high|critical)$")
    hour_utc: int | None = Field(default=None, ge=0, le=23)


class AbacViolationItem(BaseModel):
    rule: str
    message: str
    severity: str


class AbacEvaluateResponse(BaseModel):
    allow: bool
    available: bool
    skipped: bool = False
    violations: list[AbacViolationItem] = Field(default_factory=list)
    error: str | None = None


class VaultStatusResponse(BaseModel):
    enabled: bool
    available: bool
    authenticated: bool
    addr: str
    auth_method: str | None = None
    mount_path: str
    secrets_backend: str
    jwt_from_vault: bool
    jwt_secret_insecure: bool
    error: str | None = None
