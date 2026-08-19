from typing import Literal

from pydantic import BaseModel, Field


class McpScopeEntry(BaseModel):
    server_id: str
    tool_names: list[str] = Field(default_factory=list)


class McpScopeConfig(BaseModel):
    mode: str = "all"
    entries: list[McpScopeEntry] = Field(default_factory=list)


class PolicyBundleResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    is_default: bool
    policy_ids: list[str]
    custom_intent_ids: list[str] = []
    policy_names: list[str] = []
    mcp_scope: McpScopeConfig | None = None
    target_domains: list[str] = []
    created_at: str


class PolicyBundleCreateRequest(BaseModel):
    name: str
    description: str = ""
    status: str = "active"
    is_default: bool = False
    policy_ids: list[str] = []
    custom_intent_ids: list[str] = []
    mcp_scope: McpScopeConfig | None = None
    target_domains: list[str] = []


class PolicyBundleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    is_default: bool | None = None
    policy_ids: list[str] | None = None
    custom_intent_ids: list[str] | None = None
    mcp_scope: McpScopeConfig | None = None
    target_domains: list[str] | None = None


class ClientApiKeyResponse(BaseModel):
    id: str
    name: str
    description: str
    key_prefix: str
    key_masked: str
    bundle_id: str | None
    bundle_name: str | None = None
    client_response_protocol: str | None = None
    ai_rate_limit_rpm: int | None = None
    ai_rate_limit_rph: int | None = None
    ai_rate_limit_rpd: int | None = None
    ai_token_limit_tpm: int | None = None
    ai_token_limit_tph: int | None = None
    ai_token_limit_tpd: int | None = None
    token_saving_enabled: bool | None = None
    token_saving_mode: str | None = None
    allowed_api_origins: list[str] | None = None
    allowed_api_origins_mode: Literal["inherit", "allow_all", "restrict"] = "inherit"
    key_source: Literal["pysetu", "mirrored"] = "pysetu"
    upstream_pass_through: bool = False
    revealable: bool = False
    is_active: bool
    last_used_at: str | None = None
    created_at: str | None = None


class ClientApiKeyCreateRequest(BaseModel):
    name: str
    description: str = ""
    bundle_id: str | None = None
    client_response_protocol: str | None = None
    ai_rate_limit_rpm: int | None = None
    ai_rate_limit_rph: int | None = None
    ai_rate_limit_rpd: int | None = None
    ai_token_limit_tpm: int | None = None
    ai_token_limit_tph: int | None = None
    ai_token_limit_tpd: int | None = None
    token_saving_enabled: bool | None = None
    token_saving_mode: str | None = None
    allowed_api_origins: list[str] | None = None


class ClientApiKeyCreateResponse(ClientApiKeyResponse):
    api_key: str


class ClientApiKeyRevealResponse(BaseModel):
    id: str
    name: str
    api_key: str


class ClientApiKeyMirroredCreateRequest(BaseModel):
    name: str
    description: str = ""
    mirrored_api_key: str
    bundle_id: str | None = None
    client_response_protocol: str | None = None
    upstream_pass_through: bool = True
    ai_rate_limit_rpm: int | None = None
    ai_rate_limit_rph: int | None = None
    ai_rate_limit_rpd: int | None = None
    ai_token_limit_tpm: int | None = None
    ai_token_limit_tph: int | None = None
    ai_token_limit_tpd: int | None = None
    token_saving_enabled: bool | None = None
    token_saving_mode: str | None = None
    allowed_api_origins: list[str] | None = None


class ClientApiKeyUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    bundle_id: str | None = None
    client_response_protocol: str | None = None
    ai_rate_limit_rpm: int | None = None
    ai_rate_limit_rph: int | None = None
    ai_rate_limit_rpd: int | None = None
    ai_token_limit_tpm: int | None = None
    ai_token_limit_tph: int | None = None
    ai_token_limit_tpd: int | None = None
    token_saving_enabled: bool | None = None
    token_saving_mode: str | None = None
    allowed_api_origins: list[str] | None = None
    upstream_pass_through: bool | None = None
    is_active: bool | None = None
