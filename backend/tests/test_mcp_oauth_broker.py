"""Tests for MCP OAuth auth mediation / token broker (BL-067 / S12-03)."""

from datetime import UTC, datetime, timedelta

from app.services.mcp_oauth_broker_service import (
    OAuthBrokerState,
    apply_token_grant,
    authorization_header,
    build_token_form,
    needs_token_fetch,
    parse_token_response,
    public_oauth_status,
    token_is_fresh,
)
from app.services.mcp_transport import build_mcp_headers


def _state(**kwargs) -> OAuthBrokerState:
    defaults = dict(
        enabled=True,
        grant_type="client_credentials",
        token_url="https://idp.example/oauth/token",
        client_id="mcp-client",
        scopes="mcp.read mcp.write",
        token_expires_at=None,
        client_secret="s3cret",
        refresh_token=None,
        access_token=None,
    )
    defaults.update(kwargs)
    return OAuthBrokerState(**defaults)


def test_token_is_fresh_respects_skew() -> None:
    now = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    soon = now + timedelta(seconds=30)
    later = now + timedelta(minutes=10)
    assert token_is_fresh(soon, now=now, skew_seconds=60) is False
    assert token_is_fresh(later, now=now, skew_seconds=60) is True
    assert token_is_fresh(None, now=now) is False


def test_needs_token_fetch_for_missing_or_expired() -> None:
    now = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    assert needs_token_fetch(_state(access_token=None), now=now) is True
    assert needs_token_fetch(
        _state(access_token="tok", token_expires_at=now + timedelta(hours=1)),
        now=now,
    ) is False
    assert needs_token_fetch(_state(enabled=False, access_token=None), now=now) is False


def test_build_token_form_client_credentials() -> None:
    form = build_token_form(_state(grant_type="client_credentials"))
    assert form["grant_type"] == "client_credentials"
    assert form["client_id"] == "mcp-client"
    assert form["client_secret"] == "s3cret"
    assert form["scope"] == "mcp.read mcp.write"


def test_build_token_form_refresh_token() -> None:
    form = build_token_form(_state(grant_type="refresh_token", refresh_token="rt-1"))
    assert form["grant_type"] == "refresh_token"
    assert form["refresh_token"] == "rt-1"


def test_build_token_form_static_raises() -> None:
    try:
        build_token_form(_state(grant_type="static", access_token="abc"))
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "static" in str(exc).lower()


def test_parse_and_apply_token_grant() -> None:
    now = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    grant = parse_token_response({"access_token": "at-9", "refresh_token": "rt-9", "expires_in": 3600})
    updated = apply_token_grant(_state(access_token="old"), grant, now=now)
    assert updated.access_token == "at-9"
    assert updated.refresh_token == "rt-9"
    assert updated.token_expires_at == now + timedelta(seconds=3600)


def test_public_status_never_leaks_secrets() -> None:
    status = public_oauth_status(
        _state(access_token="super-secret-token", client_secret="shh", refresh_token="rt")
    )
    blob = str(status)
    assert "super-secret-token" not in blob
    assert "shh" not in blob
    assert status["configured"] is True
    assert status["has_client_secret"] is True
    assert status["has_refresh_token"] is True
    assert status["has_access_token"] is True
    assert status["client_id"] == "mcp-client"


def test_authorization_header_and_mcp_headers_prefer_broker_token() -> None:
    assert authorization_header("tok-1") == "Bearer tok-1"
    headers = build_mcp_headers(
        {"auth_header": "Bearer static"},
        json_rpc=True,
        access_token="broker-tok",
    )
    assert headers["Authorization"] == "Bearer broker-tok"
    assert headers["Content-Type"] == "application/json"
