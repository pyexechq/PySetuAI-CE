"""Tenant white-label branding helpers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.services.tenant_features_service import (
    feature_flags_for_api,
    feature_policy_for_api,
)

DEFAULT_PRODUCT_NAME = "PySetu AI"
DEFAULT_TAGLINE = "Governance, Gateway, and Guardrails across the Agentic Frontier"


def resolve_display_name(tenant: Tenant) -> str:
    if tenant.display_name and tenant.display_name.strip():
        return tenant.display_name.strip()
    return tenant.name


def resolve_tagline(tenant: Tenant) -> str:
    if tenant.brand_tagline and tenant.brand_tagline.strip():
        return tenant.brand_tagline.strip()
    return DEFAULT_TAGLINE


def branding_dict(tenant: Tenant) -> dict:
    flags = feature_flags_for_api(tenant)
    policy = feature_policy_for_api(tenant)
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "display_name": resolve_display_name(tenant),
        "logo_url": tenant.logo_url,
        "brand_tagline": resolve_tagline(tenant),
        "default_product_name": DEFAULT_PRODUCT_NAME,
        "default_tagline": DEFAULT_TAGLINE,
        "qa_dashboard_enabled": flags["qa_dashboard"],
        "features": flags,
        "feature_policy": policy,
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
    if "qa_dashboard_enabled" in data and data["qa_dashboard_enabled"] is not None:
        raise ValueError("Module visibility is managed by the platform operator")
    if data.get("features") is not None:
        raise ValueError("Module visibility is managed by the platform operator")
    await db.commit()
    await db.refresh(tenant)
    return tenant
