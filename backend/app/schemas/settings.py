from pydantic import BaseModel, Field

from app.schemas.tenant_features import TenantFeaturePolicyResponse, TenantFeaturesResponse


class IntegrationSettingsResponse(BaseModel):
    openai_api_key_set: bool
    openai_api_key_masked: str | None = None
    gemini_api_key_set: bool
    gemini_api_key_masked: str | None = None
    gemini_default_model: str
    ollama_enabled: bool
    ollama_base_url: str
    ollama_default_model: str
    active_upstream: str
    streaming_enabled: bool = True
    config_source: str
    secrets_backend: str = "database"
    vault_auth_method: str | None = None
    env_fallback_note: str = (
        "Environment variables (.env / Docker) are used when tenant settings are empty. "
        "Tenant settings in this page take priority."
    )


class IntegrationSettingsUpdate(BaseModel):
    openai_api_key: str | None = Field(None, description="Set to empty string to clear")
    gemini_api_key: str | None = Field(None, description="Set to empty string to clear")
    gemini_default_model: str | None = None
    ollama_enabled: bool | None = None
    ollama_base_url: str | None = None
    ollama_default_model: str | None = None


class OrganizationSettingsResponse(BaseModel):
    id: str
    name: str
    slug: str
    display_name: str
    logo_url: str | None = None
    brand_tagline: str
    default_product_name: str = "PySetu AI"
    default_tagline: str = "Governance, Gateway, and Guardrails across the Agentic Frontier"
    qa_dashboard_enabled: bool = True
    features: TenantFeaturesResponse = Field(default_factory=TenantFeaturesResponse)
    feature_policy: TenantFeaturePolicyResponse = Field(default_factory=TenantFeaturePolicyResponse)


class OrganizationSettingsUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=1024)
    brand_tagline: str | None = Field(default=None, max_length=255)
    qa_dashboard_enabled: bool | None = None
    features: TenantFeaturesResponse | None = None


class IdentitySettingsResponse(BaseModel):
    oidc_jit_provision_enabled: bool
    platform_jit_default: bool = False
    allowed_login_domains: list[str] | None = None


class IdentitySettingsUpdate(BaseModel):
    oidc_jit_provision_enabled: bool | None = None
    allowed_login_domains: list[str] | None = None


class AiAssistSettingsResponse(BaseModel):
    enabled: bool
    provider: str
    model: str
    api_key_set: bool
    api_key_masked: str | None = None
    available: bool
    features: list[str]
    air_gap_mode: bool = False


class AiAssistSettingsUpdate(BaseModel):
    enabled: bool | None = None
    provider: str | None = Field(None, description="openai or gemini")
    model: str | None = None
    api_key: str | None = Field(None, description="Set to empty string to clear")


class GatewaySettingsResponse(BaseModel):
    ai_rate_limit_rpm: int | None = None
    ai_rate_limit_rph: int | None = None
    ai_rate_limit_rpd: int | None = None
    ai_token_limit_tpm: int | None = None
    ai_token_limit_tph: int | None = None
    ai_token_limit_tpd: int | None = None
    ai_token_budgets: dict | None = None
    allowed_api_origins: list[str] | None = None


class GatewaySettingsUpdate(BaseModel):
    ai_rate_limit_rpm: int | None = Field(None, description="Requests per minute, set to 0 or null to clear")
    ai_rate_limit_rph: int | None = Field(None, description="Requests per hour, set to 0 or null to clear")
    ai_rate_limit_rpd: int | None = Field(None, description="Requests per day, set to 0 or null to clear")
    ai_token_limit_tpm: int | None = Field(None, description="Tokens per minute, set to 0 or null to clear")
    ai_token_limit_tph: int | None = Field(None, description="Tokens per hour, set to 0 or null to clear")
    ai_token_limit_tpd: int | None = Field(None, description="Tokens per day, set to 0 or null to clear")
    ai_token_budgets: dict | None = Field(None, description="Granular JSON budgets")
    allowed_api_origins: list[str] | None = None
