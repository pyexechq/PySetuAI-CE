"""Dependency health probes for operator dashboards and /health."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import async_session_factory
from app.services.opa_service import check_opa_health


async def check_database_health(db: AsyncSession | None = None) -> tuple[bool, str | None]:
    if db is not None:
        try:
            await db.execute(text("SELECT 1"))
            return True, None
        except Exception as exc:
            return False, str(exc)

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        return False, str(exc)


async def build_dependency_status() -> dict:
    db_ok, db_error = await check_database_health()
    opa_ok, opa_error = await check_opa_health()

    dependencies = {
        "database": {"status": "up" if db_ok else "down", "error": db_error},
        "opa": {
            "status": "disabled" if not settings.opa_enabled else ("up" if opa_ok else "down"),
            "error": opa_error,
        },
    }

    if not db_ok:
        overall = "unhealthy"
    elif settings.opa_enabled and not opa_ok:
        overall = "degraded"
    else:
        overall = "healthy"

    return {"status": overall, "dependencies": dependencies}
