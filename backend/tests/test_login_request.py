"""LoginRequest validation (BL-097)."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest


def test_login_request_rejects_empty_tenant_slug() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="admin@acme.com", password="secret", tenant_slug="")


def test_login_request_rejects_empty_password() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="admin@acme.com", password="", tenant_slug="acme")


def test_login_request_accepts_defaults() -> None:
    payload = LoginRequest(email="admin@acme.com", password="secret")
    assert payload.tenant_slug == "acme"
