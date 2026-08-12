"""MCP OAuth token broker — vault-backed credential mediation (BL-067)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any


ALLOWED_GRANT_TYPES = {"client_credentials", "refresh_token", "static"}


@dataclass
class OAuthBrokerState:
    enabled: bool = False
    grant_type: str = "client_credentials"
    token_url: str = ""
    client_id: str = ""
    scopes: str = ""
    token_expires_at: datetime | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    access_token: str | None = None


@dataclass
class TokenGrant:
    access_token: str
    refresh_token: str | None = None
    expires_in: int = 3600


def token_is_fresh(
    expires_at: datetime | None,
    *,
    now: datetime | None = None,
    skew_seconds: int = 60,
) -> bool:
    if expires_at is None:
        return False
    current = now or datetime.now(UTC)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return expires_at > current + timedelta(seconds=skew_seconds)


def needs_token_fetch(state: OAuthBrokerState, *, now: datetime | None = None) -> bool:
    if not state.enabled:
        return False
    if state.grant_type == "static":
        return False
    if not (state.access_token or "").strip():
        return True
    return not token_is_fresh(state.token_expires_at, now=now)


def build_token_form(state: OAuthBrokerState) -> dict[str, str]:
    grant = (state.grant_type or "client_credentials").strip().lower()
    if grant == "static":
        raise ValueError("Static grant does not fetch tokens from an IdP")
    if grant not in ALLOWED_GRANT_TYPES:
        raise ValueError(f"Unsupported grant type: {grant}")
    form: dict[str, str] = {
        "grant_type": grant,
        "client_id": state.client_id,
    }
    if state.client_secret:
        form["client_secret"] = state.client_secret
    if state.scopes.strip():
        form["scope"] = state.scopes.strip()
    if grant == "refresh_token":
        if not (state.refresh_token or "").strip():
            raise ValueError("Refresh token is required for refresh_token grant")
        form["refresh_token"] = state.refresh_token.strip()
    return form


def parse_token_response(payload: dict[str, Any]) -> TokenGrant:
    access = payload.get("access_token")
    if not isinstance(access, str) or not access.strip():
        raise ValueError("Token response missing access_token")
    refresh = payload.get("refresh_token")
    expires_in = payload.get("expires_in", 3600)
    try:
        ttl = max(60, int(expires_in))
    except (TypeError, ValueError):
        ttl = 3600
    return TokenGrant(
        access_token=access.strip(),
        refresh_token=refresh.strip() if isinstance(refresh, str) and refresh.strip() else None,
        expires_in=ttl,
    )


def apply_token_grant(
    state: OAuthBrokerState,
    grant: TokenGrant,
    *,
    now: datetime | None = None,
) -> OAuthBrokerState:
    current = now or datetime.now(UTC)
    return replace(
        state,
        access_token=grant.access_token,
        refresh_token=grant.refresh_token or state.refresh_token,
        token_expires_at=current + timedelta(seconds=grant.expires_in),
    )


def public_oauth_status(state: OAuthBrokerState | None) -> dict[str, Any]:
    if state is None or not (state.client_id or state.token_url or state.access_token):
        return {
            "configured": False,
            "enabled": False,
            "grant_type": "client_credentials",
            "token_url": "",
            "client_id": "",
            "scopes": "",
            "has_client_secret": False,
            "has_refresh_token": False,
            "has_access_token": False,
            "token_expires_at": None,
            "token_fresh": False,
        }
    return {
        "configured": True,
        "enabled": bool(state.enabled),
        "grant_type": state.grant_type,
        "token_url": state.token_url,
        "client_id": state.client_id,
        "scopes": state.scopes,
        "has_client_secret": bool(state.client_secret),
        "has_refresh_token": bool(state.refresh_token),
        "has_access_token": bool(state.access_token),
        "token_expires_at": state.token_expires_at.isoformat() if state.token_expires_at else None,
        "token_fresh": token_is_fresh(state.token_expires_at),
    }


def authorization_header(access_token: str) -> str:
    token = access_token.strip()
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def resolve_access_token_local(state: OAuthBrokerState | None) -> str | None:
    if state is None or not state.enabled:
        return None
    token = (state.access_token or "").strip()
    if not token:
        return None
    if state.grant_type == "static":
        return token
    if token_is_fresh(state.token_expires_at):
        return token
    return None


async def fetch_and_apply_token(state: OAuthBrokerState) -> OAuthBrokerState:
    import httpx

    if not state.token_url.strip():
        raise ValueError("Token URL is required")
    form = build_token_form(state)
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.post(
            state.token_url.strip(),
            data=form,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Token endpoint did not return JSON object")
    return apply_token_grant(state, parse_token_response(payload))


async def _hydrate_secrets(row) -> OAuthBrokerState:
    from app.services.secrets_service import get_mcp_oauth_secret

    client_secret = await get_mcp_oauth_secret(row.tenant_id, row.server_id, "client_secret", row.client_secret)
    refresh_token = await get_mcp_oauth_secret(row.tenant_id, row.server_id, "refresh_token", row.refresh_token)
    access_token = await get_mcp_oauth_secret(row.tenant_id, row.server_id, "access_token", row.access_token)
    return OAuthBrokerState(
        enabled=bool(row.enabled),
        grant_type=row.grant_type or "client_credentials",
        token_url=row.token_url or "",
        client_id=row.client_id or "",
        scopes=row.scopes or "",
        token_expires_at=row.token_expires_at,
        client_secret=client_secret,
        refresh_token=refresh_token,
        access_token=access_token,
    )


async def load_oauth_state(db, tenant_id, server_id) -> OAuthBrokerState | None:
    from sqlalchemy import select

    from app.models.governance import McpOAuthCredential

    result = await db.execute(
        select(McpOAuthCredential).where(
            McpOAuthCredential.tenant_id == tenant_id,
            McpOAuthCredential.server_id == server_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return await _hydrate_secrets(row)


async def save_oauth_state(db, tenant_id, server_id, payload: dict[str, Any]) -> OAuthBrokerState:
    from sqlalchemy import select

    from app.models.governance import McpOAuthCredential
    from app.services.secrets_service import set_mcp_oauth_secret

    grant = str(payload.get("grant_type") or "client_credentials").strip().lower()
    if grant not in ALLOWED_GRANT_TYPES:
        raise ValueError(f"grant_type must be one of: {', '.join(sorted(ALLOWED_GRANT_TYPES))}")

    result = await db.execute(
        select(McpOAuthCredential).where(
            McpOAuthCredential.tenant_id == tenant_id,
            McpOAuthCredential.server_id == server_id,
        )
    )
    row = result.scalar_one_or_none()
    existing = await _hydrate_secrets(row) if row is not None else OAuthBrokerState()

    def _keep_or_set(incoming: Any, current: str | None) -> str | None:
        if incoming is None:
            return current
        if isinstance(incoming, str) and not incoming.strip():
            return current
        return str(incoming).strip() if incoming else None

    enabled_value = existing.enabled if row is not None else True
    if payload.get("enabled") is not None:
        enabled_value = bool(payload.get("enabled"))

    state = OAuthBrokerState(
        enabled=enabled_value,
        grant_type=grant,
        token_url=str(payload.get("token_url") or existing.token_url or "").strip(),
        client_id=str(payload.get("client_id") or existing.client_id or "").strip(),
        scopes=str(payload.get("scopes") if payload.get("scopes") is not None else existing.scopes or "").strip(),
        token_expires_at=existing.token_expires_at,
        client_secret=_keep_or_set(payload.get("client_secret"), existing.client_secret),
        refresh_token=_keep_or_set(payload.get("refresh_token"), existing.refresh_token),
        access_token=_keep_or_set(payload.get("access_token"), existing.access_token),
    )
    if grant == "static" and not state.access_token:
        raise ValueError("Access token is required for static grant")
    if grant != "static" and not state.token_url:
        raise ValueError("Token URL is required")
    if not state.client_id and grant != "static":
        raise ValueError("Client ID is required")

    if row is None:
        row = McpOAuthCredential(tenant_id=tenant_id, server_id=server_id)
        db.add(row)

    row.enabled = state.enabled
    row.grant_type = state.grant_type
    row.token_url = state.token_url
    row.client_id = state.client_id
    row.scopes = state.scopes
    row.token_expires_at = state.token_expires_at
    row.client_secret = await set_mcp_oauth_secret(tenant_id, server_id, "client_secret", state.client_secret)
    row.refresh_token = await set_mcp_oauth_secret(tenant_id, server_id, "refresh_token", state.refresh_token)
    row.access_token = await set_mcp_oauth_secret(tenant_id, server_id, "access_token", state.access_token)
    await db.commit()
    await db.refresh(row)
    return await _hydrate_secrets(row)


async def persist_token_state(db, tenant_id, server_id, state: OAuthBrokerState) -> None:
    from sqlalchemy import select

    from app.models.governance import McpOAuthCredential
    from app.services.secrets_service import set_mcp_oauth_secret

    result = await db.execute(
        select(McpOAuthCredential).where(
            McpOAuthCredential.tenant_id == tenant_id,
            McpOAuthCredential.server_id == server_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return
    row.token_expires_at = state.token_expires_at
    row.refresh_token = await set_mcp_oauth_secret(tenant_id, server_id, "refresh_token", state.refresh_token)
    row.access_token = await set_mcp_oauth_secret(tenant_id, server_id, "access_token", state.access_token)
    await db.commit()


async def delete_oauth_state(db, tenant_id, server_id) -> bool:
    from sqlalchemy import delete, select

    from app.models.governance import McpOAuthCredential
    from app.services.secrets_service import set_mcp_oauth_secret

    result = await db.execute(
        select(McpOAuthCredential).where(
            McpOAuthCredential.tenant_id == tenant_id,
            McpOAuthCredential.server_id == server_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    await set_mcp_oauth_secret(tenant_id, server_id, "client_secret", None)
    await set_mcp_oauth_secret(tenant_id, server_id, "refresh_token", None)
    await set_mcp_oauth_secret(tenant_id, server_id, "access_token", None)
    await db.execute(
        delete(McpOAuthCredential).where(
            McpOAuthCredential.tenant_id == tenant_id,
            McpOAuthCredential.server_id == server_id,
        )
    )
    await db.commit()
    return True


async def resolve_mcp_access_token(db, server) -> str | None:
    state = await load_oauth_state(db, server.tenant_id, server.id)
    if state is None or not state.enabled:
        return None
    local = resolve_access_token_local(state)
    if local:
        return local
    if not needs_token_fetch(state):
        return state.access_token
    try:
        updated = await fetch_and_apply_token(state)
        await persist_token_state(db, server.tenant_id, server.id, updated)
        return updated.access_token
    except Exception:
        return (state.access_token or "").strip() or None
