"""Pure-unit tests for MCP SSO injection and tool deny policies."""

import uuid

import pytest

from app.services.mcp_security_service import (
    injected_headers,
    is_tool_denied,
    validate_sso_config,
)


class Config:
    def __init__(self, enabled: bool, header_name: str = "Authorization", header_format: str = "Bearer {token}", claim_extract: str = "") -> None:
        self.enabled = enabled
        self.header_name = header_name
        self.header_format = header_format
        self.claim_extract = claim_extract


class Rule:
    def __init__(self, role: str, server_id: uuid.UUID, tool_name: str) -> None:
        self.role = role
        self.server_id = server_id
        self.tool_name = tool_name


def test_injected_headers_uses_configured_claim() -> None:
    config = Config(True, header_name="X-Access-Token", header_format="Token {token}", claim_extract="sub")

    assert injected_headers(config, "raw-token", {"sub": "user-123"}) == {"X-Access-Token": "Token user-123"}


def test_disabled_sso_does_not_forward_token() -> None:
    assert injected_headers(Config(False), "secret-token") == {}


def test_missing_claim_is_rejected() -> None:
    with pytest.raises(ValueError, match="missing"):
        injected_headers(Config(True, claim_extract="access_token"), "raw-token", {})


def test_sso_header_format_requires_one_token_placeholder() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        validate_sso_config("Authorization", "Bearer token", "")


def test_tool_deny_is_case_insensitive_and_role_scoped() -> None:
    server_id = uuid.uuid4()
    rules = [Rule("finance", server_id, "delete_invoice")]

    assert is_tool_denied(rules, "finance", server_id, "DELETE_INVOICE") is True
    assert is_tool_denied(rules, "analyst", server_id, "delete_invoice") is False
    assert is_tool_denied(rules, "finance", uuid.uuid4(), "delete_invoice") is False