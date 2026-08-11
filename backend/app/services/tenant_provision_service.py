"""Platform tenant provisioning for SaaS deployments."""

from __future__ import annotations

import re
import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.demo_credentials import include_password_in_provision_response, redact_demo_users
from app.core.security import get_password_hash
from app.db.seed_governance import seed_access_for_tenant, seed_governance_for_tenant
from app.models.governance import MCPServer
from app.models.tenant import Tenant, User
from app.services.tenant_features_service import (
    apply_platform_feature_updates,
    feature_flags_for_api,
    feature_policy_for_api,
)
from app.services.tenant_invite_service import create_tenant_invite
from app.services.tenant_site_service import (
    tenant_public_url,
    validate_entry_mode,
    validate_subdomain,
)

RESERVED_TENANT_SLUGS = frozenset(
    {
        "platform",
        "admin",
        "api",
        "www",
        "auth",
        "static",
        "health",
        "docs",
    }
)

SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,98}[a-z0-9])?$")

DEMO_USER_TEMPLATES = [
    ("security", "Security Admin", "security_admin"),
    ("auditor", "Auditor User", "auditor"),
    ("compliance", "Compliance Officer", "compliance_officer"),
    ("developer", "Developer User", "developer"),
]


def normalize_slug(slug: str) -> str:
    return slug.strip().lower()


def validate_tenant_slug(slug: str) -> None:
    normalized = normalize_slug(slug)
    if not SLUG_PATTERN.fullmatch(normalized):
        raise ValueError("Slug must be 2–100 lowercase letters, numbers, or hyphens.")
    if normalized in RESERVED_TENANT_SLUGS:
        raise ValueError(f"Slug '{normalized}' is reserved.")


async def tenant_has_demo_data(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
    result = await db.execute(select(MCPServer.id).where(MCPServer.tenant_id == tenant_id).limit(1))
    return result.scalar_one_or_none() is not None


async def get_tenant_admin_email(db: AsyncSession, tenant_id: uuid.UUID) -> str | None:
    result = await db.execute(
        select(User.email)
        .where(User.tenant_id == tenant_id, User.role == "tenant_admin", User.is_active.is_(True))
        .order_by(User.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def tenant_response_dict(
    tenant: Tenant,
    *,
    demo_data_loaded: bool = False,
    admin_email: str | None = None,
) -> dict:
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "demo_data_loaded": demo_data_loaded,
        "admin_email": admin_email,
        "subdomain": tenant.subdomain or tenant.slug,
        "entry_mode": tenant.entry_mode,
        "tenant_url": tenant_public_url(tenant.subdomain or tenant.slug),
        "features": feature_flags_for_api(tenant),
        "feature_policy": feature_policy_for_api(tenant),
    }


async def list_customer_tenants(db: AsyncSession) -> list[dict]:
    platform_slug = normalize_slug(settings.platform_tenant_slug)
    result = await db.execute(
        select(Tenant)
        .where(Tenant.slug != platform_slug)
        .order_by(Tenant.created_at.desc())
    )
    tenants = result.scalars().all()
    rows: list[dict] = []
    for tenant in tenants:
        demo_loaded = await tenant_has_demo_data(db, tenant.id)
        admin_email = await get_tenant_admin_email(db, tenant.id)
        rows.append(tenant_response_dict(tenant, demo_data_loaded=demo_loaded, admin_email=admin_email))
    return rows


async def get_customer_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> dict | None:
    platform_slug = normalize_slug(settings.platform_tenant_slug)
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id, Tenant.slug != platform_slug))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        return None
    demo_loaded = await tenant_has_demo_data(db, tenant.id)
    admin_email = await get_tenant_admin_email(db, tenant.id)
    return tenant_response_dict(tenant, demo_data_loaded=demo_loaded, admin_email=admin_email)


async def _ensure_subdomain_available(
    db: AsyncSession,
    subdomain: str | None,
    *,
    exclude_tenant_id: uuid.UUID | None = None,
) -> None:
    if not subdomain:
        return
    query = select(Tenant.id).where(Tenant.subdomain == subdomain)
    if exclude_tenant_id is not None:
        query = query.where(Tenant.id != exclude_tenant_id)
    existing = await db.execute(query)
    if existing.scalar_one_or_none() is not None:
        raise ValueError(f"Subdomain '{subdomain}' is already in use.")


async def provision_tenant(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    admin_email: str,
    admin_name: str,
    admin_password: str,
    include_demo_data: bool = False,
    is_active: bool = True,
    subdomain: str | None = None,
    entry_mode: str = "login_only",
    send_admin_invite: bool = False,
    send_invite_email: bool = True,
    invite_template_slug: str = "professional_welcome",
) -> dict:
    validate_tenant_slug(slug)
    normalized_slug = normalize_slug(slug)
    normalized_email = admin_email.strip().lower()
    normalized_entry_mode = validate_entry_mode(entry_mode)
    normalized_subdomain = validate_subdomain(subdomain or normalized_slug, tenant_slug=normalized_slug)

    if send_admin_invite:
        effective_password = secrets.token_urlsafe(24)
    elif not admin_password:
        raise ValueError("Admin password is required unless send_admin_invite is enabled.")
    else:
        effective_password = admin_password

    existing_slug = await db.execute(select(Tenant.id).where(func.lower(Tenant.slug) == normalized_slug))
    if existing_slug.scalar_one_or_none() is not None:
        raise ValueError(f"Tenant slug '{normalized_slug}' is already in use.")
    await _ensure_subdomain_available(db, normalized_subdomain)

    tenant = Tenant(
        name=name.strip(),
        slug=normalized_slug,
        is_active=is_active,
        subdomain=normalized_subdomain,
        entry_mode=normalized_entry_mode,
    )
    db.add(tenant)
    await db.flush()

    db.add(
        User(
            tenant_id=tenant.id,
            email=normalized_email,
            name=admin_name.strip(),
            hashed_password=get_password_hash(effective_password),
            role="tenant_admin",
        )
    )

    demo_users: list[dict[str, str]] = []
    if not send_admin_invite:
        demo_users.append(
            {
                "email": normalized_email,
                "name": admin_name.strip(),
                "role": "tenant_admin",
                **(
                    {"password": effective_password}
                    if include_password_in_provision_response()
                    else {}
                ),
            }
        )

    if include_demo_data:
        domain = f"{normalized_slug}.demo.local"
        for local_part, display_name, role in DEMO_USER_TEMPLATES:
            email = f"{local_part}@{domain}"
            db.add(
                User(
                    tenant_id=tenant.id,
                    email=email,
                    name=display_name,
                    hashed_password=get_password_hash(effective_password),
                    role=role,
                )
            )
            user_entry: dict[str, str] = {
                "email": email,
                "name": display_name,
                "role": role,
            }
            if include_password_in_provision_response():
                user_entry["password"] = effective_password
            demo_users.append(user_entry)

        await seed_governance_for_tenant(db, tenant.id)
        await seed_access_for_tenant(db, tenant.id)

    admin_invite = None
    if send_admin_invite:
        admin_invite = await create_tenant_invite(
            db,
            tenant=tenant,
            email=normalized_email,
            role="tenant_admin",
            admin_name=admin_name.strip(),
            template_slug=invite_template_slug,
            send_email=send_invite_email,
        )

    await db.commit()
    await db.refresh(tenant)

    demo_loaded = include_demo_data or await tenant_has_demo_data(db, tenant.id)
    message = "Tenant provisioned."
    if include_demo_data:
        message = "Tenant provisioned with demo data."
    elif send_admin_invite and admin_invite:
        if admin_invite.get("email_sent"):
            message = "Tenant provisioned and admin invite email sent."
        elif admin_invite.get("email_status") == "smtp_disabled":
            message = "Tenant provisioned. SMTP is disabled — copy the invite link below."
        else:
            message = "Tenant provisioned. Share the admin invite link to complete onboarding."

    return {
        "tenant": tenant_response_dict(
            tenant,
            demo_data_loaded=demo_loaded,
            admin_email=normalized_email,
        ),
        "demo_users": redact_demo_users(demo_users) if include_demo_data else demo_users,
        "message": message,
        "admin_invite": admin_invite,
    }


async def update_customer_tenant(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str | None = None,
    is_active: bool | None = None,
    subdomain: str | None = None,
    entry_mode: str | None = None,
    clear_subdomain: bool = False,
    features: dict[str, bool | None] | None = None,
    feature_policy: dict[str, dict[str, bool | None] | None] | None = None,
) -> dict | None:
    platform_slug = normalize_slug(settings.platform_tenant_slug)
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id, Tenant.slug != platform_slug))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        return None

    if name is not None:
        tenant.name = name.strip()
    if is_active is not None:
        tenant.is_active = is_active
    if entry_mode is not None:
        tenant.entry_mode = validate_entry_mode(entry_mode)
    if clear_subdomain:
        tenant.subdomain = tenant.slug
    elif subdomain is not None:
        normalized_subdomain = validate_subdomain(subdomain, tenant_slug=tenant.slug)
        await _ensure_subdomain_available(db, normalized_subdomain, exclude_tenant_id=tenant.id)
        tenant.subdomain = normalized_subdomain

    if features:
        tenant_editable: dict[str, bool | None] = {}
        if feature_policy:
            for key, entry in feature_policy.items():
                if isinstance(entry, dict) and "tenant_editable" in entry:
                    tenant_editable[key] = entry.get("tenant_editable")
        apply_platform_feature_updates(tenant, features, tenant_editable=tenant_editable or None)

    await db.commit()
    await db.refresh(tenant)

    demo_loaded = await tenant_has_demo_data(db, tenant.id)
    admin_email = await get_tenant_admin_email(db, tenant.id)
    return tenant_response_dict(tenant, demo_data_loaded=demo_loaded, admin_email=admin_email)
