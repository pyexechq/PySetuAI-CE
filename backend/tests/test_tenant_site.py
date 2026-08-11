"""Tests for tenant public site resolution."""

from app.services.tenant_site_service import extract_subdomain_from_host, validate_entry_mode


def test_extract_subdomain_from_localhost_dev_host() -> None:
    assert extract_subdomain_from_host("acme.localhost:3000") == "acme"


def test_extract_subdomain_ignores_bare_localhost() -> None:
    assert extract_subdomain_from_host("localhost:3000") is None


def test_validate_entry_mode_accepts_marketing_site() -> None:
    assert validate_entry_mode("marketing_site") == "marketing_site"
