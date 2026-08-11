from pydantic import BaseModel, Field


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
    default_product_name: str = "HelixGuard AI"
    default_tagline: str = "Enterprise AI Control Plane"


class OrganizationSettingsUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=1024)
    brand_tagline: str | None = Field(default=None, max_length=255)
