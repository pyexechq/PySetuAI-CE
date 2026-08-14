"""Unit tests for MCP bundle scope and deny enforcement."""

import uuid

from app.models.governance import PolicyBundle
from app.services.mcp_access_service import (
    CLIENT_KEY_ROLE,
    check_tool_access,
    filter_servers_for_bundle,
    is_tool_in_bundle_scope,
    parse_mcp_scope,
    resolve_actor_role,
)
from app.services.mcp_security_service import is_tool_denied


class Server:
    def __init__(self, server_id: uuid.UUID, name: str = "srv") -> None:
        self.id = server_id
        self.name = name


class Rule:
    def __init__(self, role: str, server_id: uuid.UUID, tool_name: str) -> None:
        self.role = role
        self.server_id = server_id
        self.tool_name = tool_name


class Ctx:
    def __init__(self, user=None, client_api_key_id=None) -> None:
        self.user = user
        self.client_api_key_id = client_api_key_id


class User:
    def __init__(self, role: str) -> None:
        self.role = role


def test_parse_mcp_scope_defaults_to_all() -> None:
    scope = parse_mcp_scope(None)
    assert scope["mode"] == "all"


def test_filter_servers_allowlist() -> None:
    server_a = Server(uuid.uuid4(), "a")
    server_b = Server(uuid.uuid4(), "b")
    bundle = PolicyBundle(
        tenant_id=uuid.uuid4(),
        name="b1",
        mcp_scope={"mode": "allowlist", "entries": [{"server_id": str(server_a.id), "tool_names": []}]},
    )
    filtered = filter_servers_for_bundle([server_a, server_b], bundle)
    assert filtered == [server_a]


def test_tool_in_bundle_scope_with_tool_names() -> None:
    server_id = uuid.uuid4()
    bundle = PolicyBundle(
        tenant_id=uuid.uuid4(),
        name="b1",
        mcp_scope={
            "mode": "allowlist",
            "entries": [{"server_id": str(server_id), "tool_names": ["read_only"]}],
        },
    )
    ok, _ = is_tool_in_bundle_scope(bundle, server_id, "read_only")
    denied, reason = is_tool_in_bundle_scope(bundle, server_id, "delete_all")
    assert ok is True
    assert denied is False
    assert "not allowed" in reason


def test_check_tool_access_deny_rule() -> None:
    server_id = uuid.uuid4()
    server = Server(server_id)
    rules = [Rule(CLIENT_KEY_ROLE, server_id, "danger")]
    allowed, _ = check_tool_access(None, rules, CLIENT_KEY_ROLE, server, "safe")
    denied, reason = check_tool_access(None, rules, CLIENT_KEY_ROLE, server, "danger")
    assert allowed is True
    assert denied is False
    assert "denied" in reason


def test_resolve_actor_role() -> None:
    assert resolve_actor_role(Ctx(user=User("analyst"))) == "analyst"
    assert resolve_actor_role(Ctx()) == CLIENT_KEY_ROLE
