"""PySetu client API keys for ingress authentication."""

from __future__ import annotations

import base64
import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.governance import ClientApiKey, PolicyBundle
from app.models.tenant import Tenant
from app.modules.uag.client_response import INHERIT_CLIENT_PROTOCOL, normalize_client_protocol

KEY_PREFIX = "hg_"
KEY_SOURCE_PYSETU = "pysetu"
KEY_SOURCE_MIRRORED = "mirrored"
MAX_API_ORIGINS = 50
_LOCALHOST_ORIGIN = re.compile(r"^https?://localhost(:\d+)?$", re.IGNORECASE)
_EXTENSION_ORIGIN = re.compile(r"^(chrome|edge)-extension://[a-p]{32}$", re.IGNORECASE)


def hash_client_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _fernet() -> Fernet:
    secret = settings.client_key_encryption_key or settings.jwt_secret_key
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_client_key(raw_key: str) -> str:
    return _fernet().encrypt(raw_key.encode("utf-8")).decode("utf-8")


def decrypt_client_key(encrypted: str) -> str:
    try:
        return _fernet().decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ValueError("Unable to decrypt client API key") from exc


def looks_like_jwt(token: str) -> bool:
    parts = token.split(".")
    return len(parts) == 3 and all(part.strip() for part in parts)


def generate_client_key() -> tuple[str, str, str]:
    """Return (full_key, key_prefix, key_hash)."""
    suffix = secrets.token_urlsafe(24)
    full_key = f"{KEY_PREFIX}{suffix}"
    key_prefix = full_key[:12]
    return full_key, key_prefix, hash_client_key(full_key)


def mirrored_key_prefix(raw_key: str) -> str:
    trimmed = raw_key.strip()
    return trimmed[:12] if len(trimmed) >= 12 else trimmed


def normalize_origin(origin: str) -> str:
    value = origin.strip().rstrip("/")
    if not value:
        raise ValueError("Origin cannot be empty")
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid origin URL: {origin}")
    if parsed.scheme in {"chrome-extension", "edge-extension"}:
        if parsed.path not in {"", "/"} or not _EXTENSION_ORIGIN.fullmatch(value):
            raise ValueError(f"Invalid browser extension origin: {origin}")
        return f"{parsed.scheme}://{parsed.netloc}"
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Origin must use http or https: {origin}")
    if parsed.path not in {"", "/"}:
        raise ValueError(f"Origin must not include a path: {origin}")
    if parsed.scheme == "http" and not _LOCALHOST_ORIGIN.match(value):
        raise ValueError(f"Non-localhost origins must use https: {origin}")
    return f"{parsed.scheme}://{parsed.netloc}"


def validate_api_origins(origins: list[str] | None) -> list[str] | None:
    """Validate and normalize origin allowlists. None = inherit; [] = allow all."""
    if origins is None:
        return None
    if not origins:
        return []
    if len(origins) > MAX_API_ORIGINS:
        raise ValueError(f"At most {MAX_API_ORIGINS} origins are allowed")
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in origins:
        origin = normalize_origin(raw)
        if origin in seen:
            continue
        seen.add(origin)
        normalized.append(origin)
    return normalized


def resolve_effective_api_origins(key: ClientApiKey, tenant: Tenant | None) -> list[str] | None:
    """Return enforced origin list, or None when any origin is allowed."""
    key_origins = key.allowed_api_origins
    if key_origins is not None:
        if len(key_origins) == 0:
            return None
        return list(key_origins)

    tenant_origins = tenant.allowed_api_origins if tenant else None
    if tenant_origins:
        return list(tenant_origins)
    return None


def allowed_api_origins_mode(key: ClientApiKey) -> Literal["inherit", "allow_all", "restrict"]:
    if key.allowed_api_origins is None:
        return "inherit"
    if len(key.allowed_api_origins) == 0:
        return "allow_all"
    return "restrict"


async def _key_hash_exists(db: AsyncSession, key_hash: str) -> bool:
    result = await db.execute(select(ClientApiKey.id).where(ClientApiKey.key_hash == key_hash).limit(1))
    return result.scalar_one_or_none() is not None


async def resolve_client_api_key(db: AsyncSession, raw_key: str) -> ClientApiKey | None:
    trimmed = raw_key.strip()
    if not trimmed:
        return None
    key_hash = hash_client_key(trimmed)
    result = await db.execute(
        select(ClientApiKey).where(
            ClientApiKey.key_hash == key_hash,
            ClientApiKey.is_active.is_(True),
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None
    record.last_used_at = datetime.now(UTC)
    return record


async def get_client_api_key(db: AsyncSession, tenant_id: uuid.UUID, key_id: str) -> ClientApiKey:
    from fastapi import HTTPException, status

    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client API key id") from exc

    result = await db.execute(
        select(ClientApiKey).where(ClientApiKey.id == key_uuid, ClientApiKey.tenant_id == tenant_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client API key not found")
    return record


async def validate_bundle_for_tenant(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    bundle_id: str | None,
) -> uuid.UUID | None:
    from fastapi import HTTPException, status

    if not bundle_id:
        return None
    try:
        bundle_uuid = uuid.UUID(bundle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bundle id") from exc

    result = await db.execute(
        select(PolicyBundle).where(PolicyBundle.id == bundle_uuid, PolicyBundle.tenant_id == tenant_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Policy bundle not found")
    return bundle_uuid


def normalize_api_key_client_protocol(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"", INHERIT_CLIENT_PROTOCOL, "default", "auto"}:
        return None
    return normalize_client_protocol(normalized)


def normalize_token_saving_mode(value: str | None) -> str | None:
    if value is None:
        return None
    mode = value.strip().lower()
    if mode in {"", "inherit", "default"}:
        return None
    if mode not in ("json_to_toon", "strip_markdown", "both"):
        return "both"
    return mode


def client_key_response(record: ClientApiKey, *, bundle_name: str | None = None) -> dict:
    return {
        "id": str(record.id),
        "name": record.name,
        "description": record.description or "",
        "key_prefix": record.key_prefix,
        "key_masked": f"{record.key_prefix}••••",
        "bundle_id": str(record.bundle_id) if record.bundle_id else None,
        "bundle_name": bundle_name,
        "client_response_protocol": record.client_response_protocol,
        "ai_rate_limit_rpm": record.ai_rate_limit_rpm,
        "ai_rate_limit_rph": record.ai_rate_limit_rph,
        "ai_rate_limit_rpd": record.ai_rate_limit_rpd,
        "ai_token_limit_tpm": record.ai_token_limit_tpm,
        "ai_token_limit_tph": record.ai_token_limit_tph,
        "ai_token_limit_tpd": record.ai_token_limit_tpd,
        "token_saving_enabled": record.token_saving_enabled,
        "token_saving_mode": record.token_saving_mode,
        "allowed_api_origins": record.allowed_api_origins,
        "allowed_api_origins_mode": allowed_api_origins_mode(record),
        "key_source": record.key_source or KEY_SOURCE_PYSETU,
        "upstream_pass_through": bool(record.upstream_pass_through),
        "revealable": bool(record.key_encrypted),
        "is_active": record.is_active,
        "last_used_at": record.last_used_at.isoformat() if record.last_used_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


async def register_mirrored_client_key(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str,
    raw_key: str,
    description: str = "",
    bundle_id: uuid.UUID | None = None,
    client_response_protocol: str | None = None,
    upstream_pass_through: bool = True,
    allowed_api_origins: list[str] | None = None,
    ai_rate_limit_rpm: int | None = None,
    ai_rate_limit_rph: int | None = None,
    ai_rate_limit_rpd: int | None = None,
    ai_token_limit_tpm: int | None = None,
    ai_token_limit_tph: int | None = None,
    ai_token_limit_tpd: int | None = None,
    token_saving_enabled: bool | None = None,
    token_saving_mode: str | None = None,
) -> ClientApiKey:
    from fastapi import HTTPException, status

    trimmed_key = raw_key.strip()
    if len(trimmed_key) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mirrored API key is too short")

    key_hash = hash_client_key(trimmed_key)
    if await _key_hash_exists(db, key_hash):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This API key is already registered")

    record = ClientApiKey(
        tenant_id=tenant_id,
        name=name,
        description=description,
        key_prefix=mirrored_key_prefix(trimmed_key),
        key_hash=key_hash,
        key_encrypted=encrypt_client_key(trimmed_key),
        bundle_id=bundle_id,
        client_response_protocol=client_response_protocol,
        allowed_api_origins=allowed_api_origins,
        key_source=KEY_SOURCE_MIRRORED,
        upstream_pass_through=upstream_pass_through,
        ai_rate_limit_rpm=ai_rate_limit_rpm,
        ai_rate_limit_rph=ai_rate_limit_rph,
        ai_rate_limit_rpd=ai_rate_limit_rpd,
        ai_token_limit_tpm=ai_token_limit_tpm,
        ai_token_limit_tph=ai_token_limit_tph,
        ai_token_limit_tpd=ai_token_limit_tpd,
        token_saving_enabled=token_saving_enabled,
        token_saving_mode=token_saving_mode,
        is_active=True,
    )
    db.add(record)
    return record
