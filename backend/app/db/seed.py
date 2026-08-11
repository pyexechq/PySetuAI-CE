import asyncio

from sqlalchemy import select

from app.config import settings
from app.core.security import get_password_hash
from app.db import async_session_factory
from app.models.tenant import Tenant, User

DEMO_TENANT = {
    "name": "Acme Corporation",
    "slug": "acme",
}

PLATFORM_TENANT = {
    "name": "HelixGuard Platform",
    "slug": "platform",
}

PLATFORM_ADMIN = {
    "email": "platform@helixguard.com",
    "name": "Platform Administrator",
    "password": "platform1234",
    "role": "platform_admin",
}

DEMO_USERS = [
    {
        "email": "admin@acme.com",
        "name": "Admin User",
        "password": "demo1234",
        "role": "tenant_admin",
    },
    {
        "email": "security@acme.com",
        "name": "Security Admin",
        "password": "demo1234",
        "role": "security_admin",
    },
    {
        "email": "auditor@acme.com",
        "name": "Auditor User",
        "password": "demo1234",
        "role": "auditor",
    },
    {
        "email": "compliance@acme.com",
        "name": "Compliance Officer",
        "password": "demo1234",
        "role": "compliance_officer",
    },
    {
        "email": "developer@acme.com",
        "name": "Developer User",
        "password": "demo1234",
        "role": "developer",
    },
]


async def seed_demo_data() -> None:
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

        for demo_user in DEMO_USERS:
            user_result = await session.execute(
                select(User).where(User.tenant_id == tenant.id, User.email == demo_user["email"])
            )
            if user_result.scalar_one_or_none() is None:
                session.add(
                    User(
                        tenant_id=tenant.id,
                        email=demo_user["email"],
                        name=demo_user["name"],
                        hashed_password=get_password_hash(demo_user["password"]),
                        role=demo_user["role"],
                    )
                )

        await session.commit()


async def seed_platform_admin() -> None:
    if not settings.platform_portal_enabled:
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
                    User.email == "platform@helixguard.local",
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
                        hashed_password=get_password_hash(PLATFORM_ADMIN["password"]),
                        role=PLATFORM_ADMIN["role"],
                    )
                )

        await session.commit()


def main() -> None:
    asyncio.run(seed_demo_data())
    print("Seed data applied successfully.")


if __name__ == "__main__":
    main()
