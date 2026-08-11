"""Demo credential helpers — keep known passwords out of production bundles."""

from __future__ import annotations

from app.config import settings


def demo_credentials_allowed() -> bool:
    """True when debug or explicit demo mode is enabled (never in production)."""
    return settings.debug or settings.demo_credentials_enabled


def resolve_demo_seed_password() -> str | None:
    """Password for local demo seed users; must come from env when demo mode is on."""
    if not demo_credentials_allowed():
        return None
    value = (settings.demo_seed_password or "").strip()
    return value or None


def resolve_platform_admin_password() -> str | None:
    """Password for the seeded platform admin account."""
    if not demo_credentials_allowed():
        return None
    value = (settings.demo_platform_admin_password or "").strip()
    return value or None


def include_password_in_provision_response() -> bool:
    """Whether tenant provisioning API responses may echo plaintext passwords."""
    return demo_credentials_allowed()


def redact_demo_users(users: list[dict[str, str]]) -> list[dict[str, str]]:
    """Strip password fields from provision responses when demo mode is off."""
    if include_password_in_provision_response():
        return users
    return [{key: value for key, value in user.items() if key != "password"} for user in users]
