"""Gateway caller context for JWT users and client API keys."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models.tenant import User


@dataclass
class GatewayContext:
    tenant_id: uuid.UUID
    actor: str
    user: User | None = None
    client_api_key_id: uuid.UUID | None = None
    client_api_key_name: str | None = None
    policy_bundle_id: uuid.UUID | None = None
    policy_bundle_name: str | None = None
    client_response_protocol: str | None = None
    ai_rate_limit_rpm: int | None = None
    ai_rate_limit_rph: int | None = None
    ai_rate_limit_rpd: int | None = None
    ai_token_limit_tpm: int | None = None
    ai_token_limit_tph: int | None = None
    ai_token_limit_tpd: int | None = None
    token_saving_enabled: bool | None = None
    token_saving_mode: str | None = None
    key_source: str = "pysetu"
    upstream_pass_through: bool = False
    ingress_bearer_token: str | None = None
    debug_mode: bool = False
