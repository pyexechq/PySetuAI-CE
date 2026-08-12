"""Tests for self-service MCP portal (BL-070 / S12-06)."""

from app.services.mcp_portal_service import (
    connection_status,
    portal_visible,
    server_auth_required,
    set_portal_visible,
)


class FakeServer:
    def __init__(self, name="Test", connection_config=None):
        self.name = name
        self.connection_config = connection_config or {}
        self.status = "healthy"
        self.tools_count = 3
        self.tool_names = ["read_file"]
        self.category = "Developer"
        self.id = "00000000-0000-0000-0000-000000000001"


def test_portal_visible_defaults_true() -> None:
    server = FakeServer(connection_config={"catalog_slug": "github"})
    assert portal_visible(server) is True


def test_portal_visible_explicit_false() -> None:
    server = FakeServer(connection_config={"portal_visible": False})
    assert portal_visible(server) is False


def test_set_portal_visible() -> None:
    server = FakeServer()
    set_portal_visible(server, False)
    assert server.connection_config["portal_visible"] is False


def test_server_auth_required_from_catalog() -> None:
    server = FakeServer(connection_config={"catalog_slug": "github"})
    assert server_auth_required(server) is True
    server = FakeServer(connection_config={"catalog_slug": "filesystem"})
    assert server_auth_required(server) is False


def test_connection_status_ready_without_auth() -> None:
    server = FakeServer(connection_config={"catalog_slug": "filesystem"})
    assert connection_status(server, user_connected=False, tenant_token_available=False) == "ready"


def test_connection_status_needs_auth() -> None:
    server = FakeServer(connection_config={"catalog_slug": "github"})
    assert connection_status(server, user_connected=False, tenant_token_available=False) == "needs_auth"


def test_connection_status_connected_user_token() -> None:
    server = FakeServer(connection_config={"catalog_slug": "github"})
    assert connection_status(server, user_connected=True, tenant_token_available=False) == "connected"


def test_connection_status_connected_tenant_token() -> None:
    server = FakeServer(connection_config={"catalog_slug": "github"})
    assert connection_status(server, user_connected=False, tenant_token_available=True) == "connected"
