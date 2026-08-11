"""Tenant public site resolution and validation."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import Tenant

VALID_ENTRY_MODES = frozenset({"login_only", "marketing_site"})
SUBDOMAIN_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,98}[a-z0-9])?$")

RESERVED_SUBDOMAINS = frozenset(
    {
        "www",
        "app",
        "api",
        "platform",
        "admin",
        "mail",
        "static",
        "auth",
        "login",
    }
)


def normalize_subdomain(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def validate_subdomain(subdomain: str | None, *, tenant_slug: str | None = None) -> str | None:
    normalized = normalize_subdomain(subdomain)
    if normalized is None:
        return None
    if not SUBDOMAIN_PATTERN.fullmatch(normalized):
        raise ValueError("Subdomain must be 2–100 lowercase letters, numbers, or hyphens.")
    if normalized in RESERVED_SUBDOMAINS:
        raise ValueError(f"Subdomain '{normalized}' is reserved.")
    if tenant_slug and normalized == tenant_slug.strip().lower():
        return normalized
    return normalized


def validate_entry_mode(entry_mode: str) -> str:
    normalized = entry_mode.strip().lower()
    if normalized not in VALID_ENTRY_MODES:
        raise ValueError("Entry mode must be 'login_only' or 'marketing_site'.")
    return normalized


def extract_subdomain_from_host(host: str) -> str | None:
    hostname = host.split(":")[0].strip().lower()
    if not hostname or hostname in {"localhost", "127.0.0.1"}:
        return None

    base_domain = settings.app_base_domain.strip().lower()
    if not base_domain:
        return None

    if hostname == base_domain or hostname == f"www.{base_domain}":
        return None

    if hostname.endswith(f".{base_domain}"):
        prefix = hostname[: -(len(base_domain) + 1)]
        if prefix and "." not in prefix:
            return prefix
        return None

    # Local dev: acme.localhost
    if hostname.endswith(".localhost"):
        prefix = hostname.removesuffix(".localhost")
        if prefix and "." not in prefix:
            return prefix

    return None


def public_site_dict(tenant: Tenant) -> dict:
    subdomain = tenant.subdomain or tenant.slug
    return {
        "slug": tenant.slug,
        "name": tenant.name,
        "display_name": tenant.display_name or tenant.name,
        "logo_url": tenant.logo_url,
        "brand_tagline": tenant.brand_tagline or "Enterprise AI Control Plane",
        "subdomain": subdomain,
        "entry_mode": tenant.entry_mode,
        "login_path": f"/login?tenant={tenant.slug}",
        "tenant_url": tenant_public_url(subdomain),
    }


def tenant_public_url(subdomain: str) -> str:
    base = settings.app_base_domain.strip()
    scheme = settings.app_base_scheme
    if not base or base.startswith("localhost"):
        return f"{scheme}://{subdomain}.localhost:3000"
    return f"{scheme}://{subdomain}.{base}"


async def get_tenant_by_subdomain(db: AsyncSession, subdomain: str) -> Tenant | None:
    normalized = normalize_subdomain(subdomain)
    if not normalized:
        return None
    result = await db.execute(
        select(Tenant).where(
            Tenant.is_active.is_(True),
            Tenant.subdomain == normalized,
        )
    )
    tenant = result.scalar_one_or_none()
    if tenant is not None:
        return tenant

    result = await db.execute(
        select(Tenant).where(Tenant.is_active.is_(True), Tenant.slug == normalized)
    )
    return result.scalar_one_or_none()


async def get_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant | None:
    result = await db.execute(
        select(Tenant).where(Tenant.is_active.is_(True), Tenant.slug == slug.strip().lower())
    )
    return result.scalar_one_or_none()


async def resolve_public_site(
    db: AsyncSession,
    *,
    subdomain: str | None = None,
    slug: str | None = None,
    host: str | None = None,
) -> dict | None:
    tenant: Tenant | None = None
    if host:
        host_subdomain = extract_subdomain_from_host(host)
        if host_subdomain:
            tenant = await get_tenant_by_subdomain(db, host_subdomain)
    if tenant is None and subdomain:
        tenant = await get_tenant_by_subdomain(db, subdomain)
    if tenant is None and slug:
        tenant = await get_tenant_by_slug(db, slug)
    if tenant is None:
        return None
    return public_site_dict(tenant)
