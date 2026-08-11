from pydantic import BaseModel, Field


class OidcProviderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    issuer_url: str = Field(..., min_length=8, max_length=1024)
    client_id: str = Field(..., min_length=1, max_length=512)
    client_secret: str | None = Field(default=None, max_length=4096)
    scopes: str | None = Field(default=None, max_length=512)
    redirect_uri: str | None = Field(default=None, max_length=1024)
    role_claim: str | None = Field(default=None, max_length=128)
    role_mapping: dict[str, str] | None = None
    enabled: bool = True


class OidcProviderUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    issuer_url: str | None = Field(default=None, min_length=8, max_length=1024)
    client_id: str | None = Field(default=None, min_length=1, max_length=512)
    client_secret: str | None = Field(default=None, max_length=4096)
    scopes: str | None = Field(default=None, max_length=512)
    redirect_uri: str | None = Field(default=None, max_length=1024)
    role_claim: str | None = Field(default=None, max_length=128)
    role_mapping: dict[str, str] | None = None
    enabled: bool | None = None


class OidcProviderResponse(BaseModel):
    id: str
    name: str
    issuer_url: str
    client_id: str
    scopes: str
    redirect_uri: str
    role_claim: str
    role_mapping: dict[str, str]
    enabled: bool
    created_at: str | None = None
    client_secret_set: bool = False
    client_secret_masked: str | None = None


class OidcPublicProviderResponse(BaseModel):
    id: str
    name: str
    login_available: bool = False
    message: str = ""


class OidcAuthorizeResponse(BaseModel):
    authorization_url: str
    state: str
    provider_name: str


class OidcCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)
