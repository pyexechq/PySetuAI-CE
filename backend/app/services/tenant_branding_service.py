"""Tenant white-label branding helpers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant

DEFAULT_PRODUCT_NAME = "HelixGuard AI"
DEFAULT_TAGLINE = "Enterprise AI Control Plane"


def resolve_display_name(tenant: Tenant) -> str:
    if tenant.display_name and tenant.display_name.strip():
        return tenant.display_name.strip()
    return tenant.name


def resolve_tagline(tenant: Tenant) -> str:
    if tenant.brand_tagline and tenant.brand_tagline.strip():
        return tenant.brand_tagline.strip()
    return DEFAULT_TAGLINE


def branding_dict(tenant: Tenant) -> dict:
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "display_name": resolve_display_name(tenant),
        "logo_url": tenant.logo_url,
        "brand_tagline": resolve_tagline(tenant),
        "default_product_name": DEFAULT_PRODUCT_NAME,
        "default_tagline": DEFAULT_TAGLINE,
    }


def public_branding_dict(tenant: Tenant) -> dict:
    return {
        "slug": tenant.slug,
        "name": tenant.name,
        "display_name": resolve_display_name(tenant),
        "logo_url": tenant.logo_url,
        "brand_tagline": resolve_tagline(tenant),
    }


async def update_tenant_branding(db: AsyncSession, tenant: Tenant, data: dict) -> Tenant:
    if "name" in data and data["name"] is not None:
        tenant.name = str(data["name"]).strip()[:255]
    if "display_name" in data:
        value = data["display_name"]
        tenant.display_name = str(value).strip()[:255] if value and str(value).strip() else None
    if "logo_url" in data:
        value = data["logo_url"]
        tenant.logo_url = str(value).strip()[:1024] if value and str(value).strip() else None
    if "brand_tagline" in data:
        value = data["brand_tagline"]
        tenant.brand_tagline = str(value).strip()[:255] if value and str(value).strip() else None
    await db.commit()
    await db.refresh(tenant)
    return tenant
