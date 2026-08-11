from pydantic import BaseModel, EmailStr, Field

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
    admin_password: str = Field(..., min_length=8, max_length=128)
    include_demo_data: bool = False
    is_active: bool = True
    subdomain: str | None = Field(default=None, min_length=2, max_length=100, pattern=r"^[a-z0-9]([a-z0-9-]{0,98}[a-z0-9])?$")
    entry_mode: str = Field(default="login_only", pattern=r"^(login_only|marketing_site)$")


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
    features: TenantFeaturesResponse
    feature_policy: TenantFeaturePolicyResponse


class PlatformTenantProvisionResponse(BaseModel):
    tenant: PlatformTenantResponse
    demo_users: list[dict[str, str]] = Field(default_factory=list)
    message: str
