"""CRUD for tenant OIDC provider configurations (Phase 5a — admin only)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import Tenant, TenantOidcProvider
from app.services.integration_service import mask_secret

DEFAULT_SCOPES = "openid profile email"
DEFAULT_ROLE_CLAIM = "groups"
VALID_ROLES = frozenset(
    {
        "platform_admin",
        "tenant_admin",
        "security_admin",
        "compliance_officer",
        "auditor",
        "developer",
    }
)


def default_redirect_uri() -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/auth/oidc/callback"


def provider_to_dict(provider: TenantOidcProvider, *, include_secret: bool = False) -> dict:
    return {
        "id": str(provider.id),
        "name": provider.name,
        "issuer_url": provider.issuer_url,
        "client_id": provider.client_id,
        "scopes": provider.scopes,
        "redirect_uri": provider.redirect_uri,
        "role_claim": provider.role_claim,
        "role_mapping": provider.role_mapping or {},
        "enabled": provider.enabled,
        "created_at": provider.created_at.isoformat() if provider.created_at else None,
        "client_secret_set": bool(provider.client_secret),
        "client_secret_masked": mask_secret(provider.client_secret) if provider.client_secret else None,
        **({"client_secret": provider.client_secret} if include_secret else {}),
    }


def public_provider_dict(provider: TenantOidcProvider) -> dict:
    from app.config import settings

    login_available = settings.oidc_enabled and provider.enabled
    return {
        "id": str(provider.id),
        "name": provider.name,
        "login_available": login_available,
        "message": "" if login_available else "OIDC login is disabled on this deployment.",
    }


async def list_providers(db: AsyncSession, tenant_id: uuid.UUID) -> list[TenantOidcProvider]:
    result = await db.execute(
        select(TenantOidcProvider)
        .where(TenantOidcProvider.tenant_id == tenant_id)
        .order_by(TenantOidcProvider.created_at.desc())
    )
    return list(result.scalars().all())


async def list_public_providers(db: AsyncSession, tenant_slug: str) -> list[TenantOidcProvider]:
    result = await db.execute(
        select(TenantOidcProvider)
        .join(Tenant, Tenant.id == TenantOidcProvider.tenant_id)
        .where(
            Tenant.slug == tenant_slug.strip().lower(),
            Tenant.is_active.is_(True),
            TenantOidcProvider.enabled.is_(True),
        )
        .order_by(TenantOidcProvider.name.asc())
    )
    return list(result.scalars().all())


async def get_provider(db: AsyncSession, tenant_id: uuid.UUID, provider_id: uuid.UUID) -> TenantOidcProvider | None:
    result = await db.execute(
        select(TenantOidcProvider).where(
            TenantOidcProvider.tenant_id == tenant_id,
            TenantOidcProvider.id == provider_id,
        )
    )
    return result.scalar_one_or_none()


def _normalize_role_mapping(raw: dict | None) -> dict[str, str]:
    if not raw:
        return {}
    normalized: dict[str, str] = {}
    for group, role in raw.items():
        role_name = str(role).strip().lower()
        if role_name not in VALID_ROLES:
            raise ValueError(f"Invalid mapped role '{role}' — use one of: {', '.join(sorted(VALID_ROLES))}")
        normalized[str(group).strip()] = role_name
    return normalized


async def create_provider(db: AsyncSession, tenant_id: uuid.UUID, data: dict) -> TenantOidcProvider:
    issuer_url = str(data["issuer_url"]).strip().rstrip("/")
    if not issuer_url.startswith("https://"):
        raise ValueError("issuer_url must use HTTPS")

    provider = TenantOidcProvider(
        tenant_id=tenant_id,
        name=str(data["name"]).strip()[:255],
        issuer_url=issuer_url[:1024],
        client_id=str(data["client_id"]).strip()[:512],
        client_secret=(str(data["client_secret"]).strip() or None) if data.get("client_secret") else None,
        scopes=str(data.get("scopes") or DEFAULT_SCOPES).strip()[:512],
        redirect_uri=str(data.get("redirect_uri") or default_redirect_uri()).strip()[:1024],
        role_claim=str(data.get("role_claim") or DEFAULT_ROLE_CLAIM).strip()[:128],
        role_mapping=_normalize_role_mapping(data.get("role_mapping")),
        enabled=bool(data.get("enabled", True)),
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


async def update_provider(
    db: AsyncSession,
    provider: TenantOidcProvider,
    data: dict,
) -> TenantOidcProvider:
    if "name" in data and data["name"] is not None:
        provider.name = str(data["name"]).strip()[:255]
    if "issuer_url" in data and data["issuer_url"] is not None:
        issuer_url = str(data["issuer_url"]).strip().rstrip("/")
        if not issuer_url.startswith("https://"):
            raise ValueError("issuer_url must use HTTPS")
        provider.issuer_url = issuer_url[:1024]
    if "client_id" in data and data["client_id"] is not None:
        provider.client_id = str(data["client_id"]).strip()[:512]
    if "client_secret" in data and data["client_secret"] is not None:
        secret = str(data["client_secret"]).strip()
        provider.client_secret = secret or None
    if "scopes" in data and data["scopes"] is not None:
        provider.scopes = str(data["scopes"]).strip()[:512] or DEFAULT_SCOPES
    if "redirect_uri" in data and data["redirect_uri"] is not None:
        provider.redirect_uri = str(data["redirect_uri"]).strip()[:1024]
    if "role_claim" in data and data["role_claim"] is not None:
        provider.role_claim = str(data["role_claim"]).strip()[:128] or DEFAULT_ROLE_CLAIM
    if "role_mapping" in data and data["role_mapping"] is not None:
        provider.role_mapping = _normalize_role_mapping(data["role_mapping"])
    if "enabled" in data and data["enabled"] is not None:
        provider.enabled = bool(data["enabled"])
    await db.commit()
    await db.refresh(provider)
    return provider


async def delete_provider(db: AsyncSession, provider: TenantOidcProvider) -> None:
    await db.delete(provider)
    await db.commit()
