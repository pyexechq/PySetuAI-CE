from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str = "acme"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    tenant_id: str


from app.schemas.tenant_features import TenantFeaturePolicyResponse, TenantFeaturesResponse


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    display_name: str | None = None
    logo_url: str | None = None
    brand_tagline: str | None = None
    qa_dashboard_enabled: bool = True
    features: TenantFeaturesResponse = Field(default_factory=TenantFeaturesResponse)
    feature_policy: TenantFeaturePolicyResponse = Field(default_factory=TenantFeaturePolicyResponse)


class TenantBrandingPublicResponse(BaseModel):
    slug: str
    name: str
    display_name: str
    logo_url: str | None = None
    brand_tagline: str


class TenantPublicSiteResponse(BaseModel):
    slug: str
    name: str
    display_name: str
    logo_url: str | None = None
    brand_tagline: str
    subdomain: str
    entry_mode: str
    login_path: str
    tenant_url: str


class DashboardMetricsResponse(BaseModel):
    total_requests: int
    blocked_requests: int
    pii_redactions: int
    policy_violations: int
    mcp_violations: int
    cost_savings: float
    compliance_score: float
    success_rate: float = 0
    total_requests_change_pct: float = 0
    blocked_requests_change_pct: float = 0
    pii_redactions_change_pct: float = 0
    policy_violations_change_pct: float = 0
    mcp_violations_change_pct: float = 0
    compliance_score_change_pts: float = 0
    success_rate_change_pts: float = 0
    comparison_period: str = "vs prior 30 days"
