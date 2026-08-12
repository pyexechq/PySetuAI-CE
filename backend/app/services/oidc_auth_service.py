"""OIDC authorization code flow with PKCE (Phase 5b)."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
import redis
from jose import jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.tenant import Tenant, TenantOidcProvider, User
from app.services.oidc_provider_service import DEFAULT_ROLE_CLAIM

STATE_TTL_SECONDS = 600
DISCOVERY_CACHE: dict[str, dict[str, Any]] = {}
JWKS_CACHE: dict[str, dict[str, Any]] = {}


def is_oidc_jit_provision_enabled(tenant: Tenant) -> bool:
    """Return True when SSO may auto-create users for this tenant."""
    return tenant.oidc_jit_provision_enabled


@dataclass
class OidcAuthorizeResult:
    authorization_url: str
    state: str
    provider_name: str


@dataclass
class OidcLoginResult:
    access_token: str
    user_id: str
    tenant_id: str
    email: str
    name: str
    role: str


def generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def _redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def _state_key(state: str) -> str:
    return f"{settings.oidc_state_redis_prefix}{state}"


def store_oidc_state(state: str, payload: dict[str, str]) -> None:
    client = _redis_client()
    client.setex(_state_key(state), STATE_TTL_SECONDS, json.dumps(payload))


def pop_oidc_state(state: str) -> dict[str, str] | None:
    client = _redis_client()
    key = _state_key(state)
    raw = client.get(key)
    if raw:
        client.delete(key)
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    return None


async def fetch_oidc_discovery(issuer_url: str) -> dict[str, Any]:
    cache_key = issuer_url.rstrip("/")
    if cache_key in DISCOVERY_CACHE:
        return DISCOVERY_CACHE[cache_key]

    url = f"{cache_key}/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid OIDC discovery document")
        DISCOVERY_CACHE[cache_key] = data
        return data


async def fetch_jwks(jwks_uri: str) -> dict[str, Any]:
    if jwks_uri in JWKS_CACHE:
        return JWKS_CACHE[jwks_uri]

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(jwks_uri)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid JWKS document")
        JWKS_CACHE[jwks_uri] = data
        return data


def resolve_role_from_claims(
    claims: dict[str, Any],
    *,
    role_claim: str,
    role_mapping: dict[str, str] | None,
    default_role: str,
) -> str:
    raw = claims.get(role_claim or DEFAULT_ROLE_CLAIM)
    groups: list[str]
    if raw is None:
        groups = []
    elif isinstance(raw, str):
        groups = [raw]
    elif isinstance(raw, list):
        groups = [str(item) for item in raw]
    else:
        groups = [str(raw)]

    mapping = role_mapping or {}
    for group in groups:
        mapped = mapping.get(group)
        if mapped:
            return mapped
    return default_role


async def get_provider_for_login(
    db: AsyncSession,
    tenant_slug: str,
    provider_id: uuid.UUID,
) -> tuple[Tenant, TenantOidcProvider]:
    result = await db.execute(
        select(Tenant, TenantOidcProvider)
        .join(TenantOidcProvider, TenantOidcProvider.tenant_id == Tenant.id)
        .where(
            Tenant.slug == tenant_slug.strip().lower(),
            Tenant.is_active.is_(True),
            TenantOidcProvider.id == provider_id,
            TenantOidcProvider.enabled.is_(True),
        )
    )
    row = result.first()
    if row is None:
        raise ValueError("OIDC provider not found or disabled")
    tenant, provider = row
    return tenant, provider


async def begin_oidc_login(
    db: AsyncSession,
    *,
    tenant_slug: str,
    provider_id: uuid.UUID,
) -> OidcAuthorizeResult:
    if not settings.oidc_enabled:
        raise ValueError("OIDC login is disabled")

    tenant, provider = await get_provider_for_login(db, tenant_slug, provider_id)
    discovery = await fetch_oidc_discovery(provider.issuer_url)
    authorization_endpoint = discovery.get("authorization_endpoint")
    if not isinstance(authorization_endpoint, str):
        raise ValueError("OIDC discovery missing authorization_endpoint")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(24)
    code_verifier, code_challenge = generate_pkce_pair()

    store_oidc_state(
        state,
        {
            "tenant_id": str(tenant.id),
            "provider_id": str(provider.id),
            "code_verifier": code_verifier,
            "nonce": nonce,
        },
    )

    params = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": provider.redirect_uri,
        "scope": provider.scopes,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    query = httpx.QueryParams(params)
    return OidcAuthorizeResult(
        authorization_url=f"{authorization_endpoint}?{query}",
        state=state,
        provider_name=provider.name,
    )


async def _verify_id_token(
    id_token: str,
    *,
    provider: TenantOidcProvider,
    discovery: dict[str, Any],
    nonce: str,
) -> dict[str, Any]:
    jwks_uri = discovery.get("jwks_uri")
    if not isinstance(jwks_uri, str):
        raise ValueError("OIDC discovery missing jwks_uri")

    header = jose_jwt.get_unverified_header(id_token)
    jwks = await fetch_jwks(jwks_uri)
    keys = jwks.get("keys", [])
    if not isinstance(keys, list):
        raise ValueError("Invalid JWKS keys")

    kid = header.get("kid")
    matching = next((key for key in keys if isinstance(key, dict) and key.get("kid") == kid), None)
    if matching is None and keys:
        matching = keys[0]
    if matching is None:
        raise ValueError("No matching JWKS key for id_token")

    issuer = discovery.get("issuer") or provider.issuer_url
    claims = jose_jwt.decode(
        id_token,
        matching,
        algorithms=[header.get("alg", "RS256")],
        audience=provider.client_id,
        issuer=issuer,
        options={"verify_at_hash": False},
    )
    if claims.get("nonce") != nonce:
        raise ValueError("OIDC nonce mismatch")
    return claims


async def complete_oidc_login(
    db: AsyncSession,
    *,
    code: str,
    state: str,
) -> OidcLoginResult:
    if not settings.oidc_enabled:
        raise ValueError("OIDC login is disabled")

    session = pop_oidc_state(state)
    if session is None:
        raise ValueError("Invalid or expired OIDC state")

    provider_uuid = uuid.UUID(session["provider_id"])
    tenant_uuid = uuid.UUID(session["tenant_id"])
    code_verifier = session["code_verifier"]
    nonce = session["nonce"]

    result = await db.execute(
        select(TenantOidcProvider).where(
            TenantOidcProvider.id == provider_uuid,
            TenantOidcProvider.tenant_id == tenant_uuid,
            TenantOidcProvider.enabled.is_(True),
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise ValueError("OIDC provider not found")

    discovery = await fetch_oidc_discovery(provider.issuer_url)
    token_endpoint = discovery.get("token_endpoint")
    if not isinstance(token_endpoint, str):
        raise ValueError("OIDC discovery missing token_endpoint")

    token_payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": provider.redirect_uri,
        "client_id": provider.client_id,
        "code_verifier": code_verifier,
    }
    if provider.client_secret:
        token_payload["client_secret"] = provider.client_secret

    async with httpx.AsyncClient(timeout=20.0) as client:
        token_response = await client.post(token_endpoint, data=token_payload)
        token_response.raise_for_status()
        token_data = token_response.json()

    id_token = token_data.get("id_token")
    if not isinstance(id_token, str):
        raise ValueError("Token response missing id_token")

    claims = await _verify_id_token(id_token, provider=provider, discovery=discovery, nonce=nonce)
    email = str(claims.get("email") or "").strip().lower()
    if not email:
        raise ValueError("OIDC id_token missing email claim")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_uuid))
    tenant = tenant_result.scalar_one()

    if tenant.allowed_login_domains:
        email_domain = email.split("@")[-1].lower()
        if email_domain not in [d.lower() for d in tenant.allowed_login_domains]:
            raise ValueError("Email domain not allowed for this tenant")

    external_subject = str(claims.get("sub") or "").strip()
    if not external_subject:
        raise ValueError("OIDC id_token missing sub claim")

    name = str(claims.get("name") or claims.get("given_name") or email.split("@")[0]).strip()[:255]
    role = resolve_role_from_claims(
        claims,
        role_claim=provider.role_claim,
        role_mapping=provider.role_mapping,
        default_role=settings.oidc_default_role,
    )

    user = await _resolve_oidc_user(
        db,
        tenant=tenant,
        email=email,
        name=name,
        role=role,
        external_subject=external_subject,
    )

    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
    )
    return OidcLoginResult(
        access_token=access_token,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        name=user.name,
        role=user.role,
    )


async def _resolve_oidc_user(
    db: AsyncSession,
    *,
    tenant: Tenant,
    email: str,
    name: str,
    role: str,
    external_subject: str,
) -> User:
    by_subject = await db.execute(
        select(User).where(
            User.tenant_id == tenant.id,
            User.auth_provider == "oidc",
            User.external_subject == external_subject,
            User.is_active.is_(True),
        )
    )
    user = by_subject.scalar_one_or_none()
    if user is not None:
        user.email = email
        user.name = name
        user.role = role
        await db.commit()
        await db.refresh(user)
        return user

    by_email = await db.execute(
        select(User).where(
            User.tenant_id == tenant.id,
            User.email == email,
            User.is_active.is_(True),
        )
    )
    user = by_email.scalar_one_or_none()
    if user is not None:
        user.auth_provider = "oidc"
        user.external_subject = external_subject
        user.name = name
        user.role = role
        await db.commit()
        await db.refresh(user)
        return user

    if not is_oidc_jit_provision_enabled(tenant):
        raise ValueError("User is not provisioned for SSO login")

    user = User(
        tenant_id=tenant.id,
        email=email,
        name=name,
        role=role,
        auth_provider="oidc",
        external_subject=external_subject,
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
