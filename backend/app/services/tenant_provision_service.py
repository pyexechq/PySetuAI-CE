"""Platform tenant provisioning for SaaS deployments."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import get_password_hash
from app.db.seed_governance import seed_access_for_tenant, seed_governance_for_tenant
from app.models.governance import MCPServer
from app.models.tenant import Tenant, User

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
) -> dict:
    validate_tenant_slug(slug)
    normalized_slug = normalize_slug(slug)
    normalized_email = admin_email.strip().lower()

    existing_slug = await db.execute(select(Tenant.id).where(func.lower(Tenant.slug) == normalized_slug))
    if existing_slug.scalar_one_or_none() is not None:
        raise ValueError(f"Tenant slug '{normalized_slug}' is already in use.")

    tenant = Tenant(name=name.strip(), slug=normalized_slug, is_active=is_active)
    db.add(tenant)
    await db.flush()

    db.add(
        User(
            tenant_id=tenant.id,
            email=normalized_email,
            name=admin_name.strip(),
            hashed_password=get_password_hash(admin_password),
            role="tenant_admin",
        )
    )

    demo_users: list[dict[str, str]] = [
        {
            "email": normalized_email,
            "name": admin_name.strip(),
            "role": "tenant_admin",
            "password": admin_password,
        }
    ]

    if include_demo_data:
        domain = f"{normalized_slug}.demo.local"
        for local_part, display_name, role in DEMO_USER_TEMPLATES:
            email = f"{local_part}@{domain}"
            db.add(
                User(
                    tenant_id=tenant.id,
                    email=email,
                    name=display_name,
                    hashed_password=get_password_hash(admin_password),
                    role=role,
                )
            )
            demo_users.append(
                {
                    "email": email,
                    "name": display_name,
                    "role": role,
                    "password": admin_password,
                }
            )

        await seed_governance_for_tenant(db, tenant.id)
        await seed_access_for_tenant(db, tenant.id)

    await db.commit()
    await db.refresh(tenant)

    demo_loaded = include_demo_data or await tenant_has_demo_data(db, tenant.id)
    return {
        "tenant": tenant_response_dict(
            tenant,
            demo_data_loaded=demo_loaded,
            admin_email=normalized_email,
        ),
        "demo_users": demo_users if include_demo_data else [],
        "message": "Tenant provisioned with demo data." if include_demo_data else "Tenant provisioned.",
    }


async def update_customer_tenant(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str | None = None,
    is_active: bool | None = None,
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

    await db.commit()
    await db.refresh(tenant)

    demo_loaded = await tenant_has_demo_data(db, tenant.id)
    admin_email = await get_tenant_admin_email(db, tenant.id)
    return tenant_response_dict(tenant, demo_data_loaded=demo_loaded, admin_email=admin_email)
