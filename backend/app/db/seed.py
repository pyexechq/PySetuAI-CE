import asyncio

from sqlalchemy import select

from app.config import settings
from app.core.demo_credentials import resolve_demo_seed_password, resolve_platform_admin_password
from app.core.security import get_password_hash
from app.db import async_session_factory
from app.models.tenant import Tenant, User

DEMO_TENANT = {
    "name": "Acme Corporation",
    "slug": "acme",
}

PLATFORM_TENANT = {
    "name": "PySetu Platform",
    "slug": "platform",
}

PLATFORM_ADMIN = {
    "email": "platform@pysetu.com",
    "name": "Platform Administrator",
    "role": "platform_admin",
}

DEMO_USER_SPECS = [
    {
        "email": "admin@acme.com",
        "name": "Admin User",
        "role": "tenant_admin",
    },
    {
        "email": "security@acme.com",
        "name": "Security Admin",
        "role": "security_admin",
    },
    {
        "email": "auditor@acme.com",
        "name": "Auditor User",
        "role": "auditor",
    },
    {
        "email": "compliance@acme.com",
        "name": "Compliance Officer",
        "role": "compliance_officer",
    },
    {
        "email": "developer@acme.com",
        "name": "Developer User",
        "role": "developer",
    },
]


async def seed_demo_data() -> None:
    demo_password = resolve_demo_seed_password()
    if demo_password is None:
        if settings.debug:
            print(
                "Demo seed skipped: set DEMO_SEED_PASSWORD in the environment to create demo users."
            )
        return

    async with async_session_factory() as session:
        tenant_result = await session.execute(select(Tenant).where(Tenant.slug == DEMO_TENANT["slug"]))
        tenant = tenant_result.scalar_one_or_none()

        if tenant is None:
            tenant = Tenant(
                name=DEMO_TENANT["name"],
                slug=DEMO_TENANT["slug"],
                subdomain=DEMO_TENANT["slug"],
                entry_mode="login_only",
            )
            session.add(tenant)
            await session.flush()
        else:
            if not tenant.subdomain:
                tenant.subdomain = DEMO_TENANT["slug"]

        for demo_user in DEMO_USER_SPECS:
            user_result = await session.execute(
                select(User).where(User.tenant_id == tenant.id, User.email == demo_user["email"])
            )
            existing_user = user_result.scalar_one_or_none()
            if existing_user is None:
                session.add(
                    User(
                        tenant_id=tenant.id,
                        email=demo_user["email"],
                        name=demo_user["name"],
                        hashed_password=get_password_hash(demo_password),
                        role=demo_user["role"],
                    )
                )
            else:
                existing_user.hashed_password = get_password_hash(demo_password)

        await session.commit()


async def seed_platform_admin() -> None:
    if not settings.platform_portal_enabled:
        return

    platform_password = resolve_platform_admin_password()
    if platform_password is None:
        if settings.debug:
            print(
                "Platform admin seed skipped: set DEMO_PLATFORM_ADMIN_PASSWORD in the environment."
            )
        return

    async with async_session_factory() as session:
        tenant_result = await session.execute(
            select(Tenant).where(Tenant.slug == settings.platform_tenant_slug)
        )
        tenant = tenant_result.scalar_one_or_none()

        if tenant is None:
            tenant = Tenant(
                name=PLATFORM_TENANT["name"],
                slug=settings.platform_tenant_slug,
            )
            session.add(tenant)
            await session.flush()

        user_result = await session.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == PLATFORM_ADMIN["email"])
        )
        if user_result.scalar_one_or_none() is None:
            legacy_result = await session.execute(
                select(User).where(
                    User.tenant_id == tenant.id,
                    User.email == "platform@pysetu.local",
                )
            )
            legacy_user = legacy_result.scalar_one_or_none()
            if legacy_user is not None:
                legacy_user.email = PLATFORM_ADMIN["email"]
            else:
                session.add(
                    User(
                        tenant_id=tenant.id,
                        email=PLATFORM_ADMIN["email"],
                        name=PLATFORM_ADMIN["name"],
                        hashed_password=get_password_hash(platform_password),
                        role=PLATFORM_ADMIN["role"],
                    )
                )

        await session.commit()


def main() -> None:
    asyncio.run(seed_demo_data())
    print("Seed data applied successfully.")


if __name__ == "__main__":
    main()
