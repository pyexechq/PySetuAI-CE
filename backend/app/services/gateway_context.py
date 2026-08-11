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
