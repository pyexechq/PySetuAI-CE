"""Tests for demo credential gating (S6-08 / BL-044)."""

from app.config import settings
from app.core.demo_credentials import (
    demo_credentials_allowed,
    include_password_in_provision_response,
    redact_demo_users,
    resolve_demo_seed_password,
    resolve_platform_admin_password,
)


def _sample_users() -> list[dict[str, str]]:
    return [
        {"email": "admin@acme.com", "name": "Admin", "role": "tenant_admin", "password": "secret"},
        {"email": "dev@acme.com", "name": "Dev", "role": "developer", "password": "secret"},
    ]


def test_demo_credentials_blocked_when_not_debug(monkeypatch) -> None:
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "demo_credentials_enabled", False)
    monkeypatch.setattr(settings, "demo_seed_password", "demo1234")

    assert demo_credentials_allowed() is False
    assert resolve_demo_seed_password() is None
    assert resolve_platform_admin_password() is None
    assert include_password_in_provision_response() is False

    redacted = redact_demo_users(_sample_users())
    assert all("password" not in user for user in redacted)
    assert redacted[0]["email"] == "admin@acme.com"


def test_demo_credentials_allowed_in_debug_with_env_password(monkeypatch) -> None:
    monkeypatch.setattr(settings, "debug", True)
    monkeypatch.setattr(settings, "demo_credentials_enabled", False)
    monkeypatch.setattr(settings, "demo_seed_password", "demo1234")
    monkeypatch.setattr(settings, "demo_platform_admin_password", "platform1234")

    assert demo_credentials_allowed() is True
    assert resolve_demo_seed_password() == "demo1234"
    assert resolve_platform_admin_password() == "platform1234"
    assert include_password_in_provision_response() is True

    preserved = redact_demo_users(_sample_users())
    assert preserved[0]["password"] == "secret"


def test_demo_credentials_explicit_flag_without_debug(monkeypatch) -> None:
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "demo_credentials_enabled", True)
    monkeypatch.setattr(settings, "demo_seed_password", "local-only")

    assert demo_credentials_allowed() is True
    assert resolve_demo_seed_password() == "local-only"
    assert include_password_in_provision_response() is True
