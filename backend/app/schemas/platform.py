from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.tenant_features import TenantFeaturePolicyResponse, TenantFeaturesResponse


class PlatformConfigResponse(BaseModel):
    enabled: bool
    deployment_mode: str
    platform_tenant_slug: str


class PlatformTenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9]([a-z0-9-]{0,98}[a-z0-9])?$")
    admin_email: EmailStr
    admin_name: str = Field(..., min_length=1, max_length=255)
    admin_password: str | None = Field(default=None, min_length=8, max_length=128)
    send_admin_invite: bool = False
    send_invite_email: bool = True
    invite_template_slug: str = Field(default="professional_welcome", min_length=1, max_length=100)
    include_demo_data: bool = False
    is_active: bool = True
    subdomain: str | None = Field(default=None, min_length=2, max_length=100, pattern=r"^[a-z0-9]([a-z0-9-]{0,98}[a-z0-9])?$")
    entry_mode: str = Field(default="login_only", pattern=r"^(login_only|marketing_site)$")

    @model_validator(mode="after")
    def validate_admin_credentials(self) -> "PlatformTenantCreateRequest":
        if not self.send_admin_invite and not self.admin_password:
            raise ValueError("admin_password is required unless send_admin_invite is enabled")
        return self


class PlatformTenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    subdomain: str | None = Field(default=None, min_length=2, max_length=100, pattern=r"^[a-z0-9]([a-z0-9-]{0,98}[a-z0-9])?$")
    entry_mode: str | None = Field(default=None, pattern=r"^(login_only|marketing_site)$")
    features: TenantFeaturesResponse | None = None
    feature_policy: TenantFeaturePolicyResponse | None = None


class PlatformTenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    created_at: str | None = None
    demo_data_loaded: bool = False
    admin_email: str | None = None
    subdomain: str
    entry_mode: str
    tenant_url: str
    features: TenantFeaturesResponse = Field(default_factory=TenantFeaturesResponse)
    feature_policy: TenantFeaturePolicyResponse = Field(default_factory=TenantFeaturePolicyResponse)


class PlatformTenantProvisionResponse(BaseModel):
    tenant: PlatformTenantResponse
    demo_users: list[dict[str, str]] = Field(default_factory=list)
    message: str
    admin_invite: "PlatformTenantInviteResponse | None" = None


class PlatformTenantInviteCreateRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="tenant_admin", min_length=1, max_length=50)
    admin_name: str | None = Field(default=None, min_length=1, max_length=255)
    template_slug: str = Field(default="professional_welcome", min_length=1, max_length=100)
    send_email: bool = True


class PlatformTenantInviteResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    role: str
    expires_at: str | None = None
    accepted_at: str | None = None
    invite_url: str
    email_template_slug: str | None = None
    email_sent: bool = False
    email_status: str | None = None
    email_sent_at: str | None = None
    email_reason: str | None = None


class InviteEmailTemplateResponse(BaseModel):
    slug: str
    name: str
    description: str
    subject: str
    html_body: str
    text_body: str
    category: str
    is_builtin: bool
    variables: list[str]
    updated_at: str | None = None


class InviteEmailTemplateUpdateRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=512)
    html_body: str = Field(..., min_length=1)
    text_body: str | None = None


class InviteEmailPreviewRequest(BaseModel):
    template_slug: str = Field(default="professional_welcome", min_length=1, max_length=100)
    tenant_name: str | None = None
    admin_name: str | None = None
    admin_email: EmailStr | None = None
    invite_url: str | None = None
    expires_at: str | None = None
    tenant_url: str | None = None


class InviteEmailPreviewResponse(BaseModel):
    template_slug: str
    subject: str
    html_body: str
    text_body: str


class PlatformOpsFleetSummary(BaseModel):
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    llm_requests_today: int
    llm_blocked_today: int
    fleet_block_rate_pct: float
    audit_events_today: int
    avg_latency_ms: int


class PlatformOpsDependencyStatus(BaseModel):
    status: str
    error: str | None = None


class PlatformOpsTenantRow(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    admin_email: str | None = None
    demo_data_loaded: bool = False
    subdomain: str
    llm_requests_today: int
    llm_blocked_today: int
    block_rate_pct: float
    audit_events_today: int
    audit_blocked_today: int
    avg_latency_ms: int
    p95_latency_ms: int


class PlatformOpsOverviewResponse(BaseModel):
    generated_at: str
    status: str
    fleet: PlatformOpsFleetSummary
    dependencies: dict[str, PlatformOpsDependencyStatus]
    tenants: list[PlatformOpsTenantRow]


class PlatformUsageFleetSummary(BaseModel):
    total_tenants: int
    active_tenants: int
    llm_requests: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    avg_tokens_per_request: float


class PlatformUsageTenantRow(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    admin_email: str | None = None
    llm_requests: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    avg_tokens_per_request: float


class PlatformUsageOverviewResponse(BaseModel):
    generated_at: str
    period_days: int
    fleet: PlatformUsageFleetSummary
    tenants: list[PlatformUsageTenantRow]


class PlatformAdminResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: str | None = None


class PlatformAdminCreateRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class PlatformAdminUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class PlatformMediaItemResponse(BaseModel):
    filename: str
    url: str
    size_bytes: int
    mime_type: str
    created_at: str


class PlatformMediaUploadResponse(BaseModel):
    url: str
    filename: str
    size_bytes: int
    mime_type: str


class ContainerHealthItem(BaseModel):
    name: str
    service: str
    status: str  # healthy, up, degraded, stopped
    image: str
    role: str
    port: str | None = None
    uptime: str | None = None
    latency_ms: int | None = None
    details: str | None = None


class ContainerHealthResponse(BaseModel):
    generated_at: str
    overall_status: str
    total_containers: int
    healthy_count: int
    containers: list[ContainerHealthItem]


class MarketingLeadItem(BaseModel):
    id: str
    full_name: str
    work_email: str
    company_name: str
    team_size: str | None = None
    use_case: str | None = None
    message: str | None = None
    status: str
    created_at: str


class MarketingPageTraffic(BaseModel):
    path: str
    title: str
    views: int
    unique_visitors: int
    conversion_rate_pct: float


class MarketingChannelTraffic(BaseModel):
    channel: str
    visitors: int
    percentage: float


class PlatformMarketingAnalyticsResponse(BaseModel):
    generated_at: str
    period_days: int
    summary: dict
    top_pages: list[MarketingPageTraffic]
    channels: list[MarketingChannelTraffic]
    recent_leads: list[MarketingLeadItem]


