"""Tests for tenant invite URL helpers."""

from app.services.tenant_invite_service import build_invite_url


def test_build_invite_url_uses_tenant_subdomain() -> None:
    url = build_invite_url("abc123token", tenant_subdomain="globex")
    assert "globex." in url
    assert "/accept-invite?token=abc123token" in url
