"""HelixGuard client API keys for ingress authentication."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import ClientApiKey, PolicyBundle

KEY_PREFIX = "hg_"


def hash_client_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_client_key() -> tuple[str, str, str]:
    """Return (full_key, key_prefix, key_hash)."""
    suffix = secrets.token_urlsafe(24)
    full_key = f"{KEY_PREFIX}{suffix}"
    key_prefix = full_key[:12]
    return full_key, key_prefix, hash_client_key(full_key)


async def resolve_client_api_key(db: AsyncSession, raw_key: str) -> ClientApiKey | None:
    if not raw_key.startswith(KEY_PREFIX):
        return None
    key_hash = hash_client_key(raw_key)
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


def client_key_response(record: ClientApiKey, *, bundle_name: str | None = None) -> dict:
    return {
        "id": str(record.id),
        "name": record.name,
        "description": record.description or "",
        "key_prefix": record.key_prefix,
        "key_masked": f"{record.key_prefix}••••",
        "bundle_id": str(record.bundle_id) if record.bundle_id else None,
        "bundle_name": bundle_name,
        "is_active": record.is_active,
        "last_used_at": record.last_used_at.isoformat() if record.last_used_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
