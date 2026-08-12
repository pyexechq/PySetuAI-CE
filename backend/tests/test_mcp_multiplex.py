"""Tests for MCP multiplex gateway (BL-065 / S12-01)."""

from app.services.mcp_multiplex_service import (
    build_multiplex_catalog,
    handle_jsonrpc,
    qualify_tool_name,
    resolve_tool_target,
    server_slug,
)


class FakeServer:
    def __init__(self, name, tool_names, connection_config=None):
        self.name = name
        self.tool_names = tool_names
        self.connection_config = connection_config or {}
        self.status = "healthy"


def test_server_slug_normalizes_name() -> None:
    assert server_slug("GitHub Docs") == "github_docs"
    assert server_slug("weather-api") == "weather_api"


def test_qualify_and_resolve_tool_target() -> None:
    servers = [
        FakeServer("GitHub Docs", ["search", "get_file"]),
        FakeServer("Weather", ["forecast"]),
    ]
    qualified = qualify_tool_name("github_docs", "search")
    assert qualified == "github_docs__search"
    target = resolve_tool_target(servers, qualified)
    assert target is not None
    assert target[0].name == "GitHub Docs"
    assert target[1] == "search"


def test_build_multiplex_catalog_prefixes_tools() -> None:
    servers = [
        FakeServer(
            "Docs",
            ["search"],
            {"tool_schemas": [{"name": "search", "description": "Find files", "inputSchema": {"type": "object"}}]},
        ),
        FakeServer("Mail", ["send_email"]),
    ]
    catalog = build_multiplex_catalog(servers)
    names = [t["name"] for t in catalog]
    assert "docs__search" in names
    assert "mail__send_email" in names
    search = next(t for t in catalog if t["name"] == "docs__search")
    assert search["description"] == "Find files"


def test_handle_jsonrpc_initialize() -> None:
    response = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, [])
    assert response["id"] == 1
    assert response["result"]["serverInfo"]["name"] == "pysetu-mcp-multiplex"
    assert "tools" in response["result"]["capabilities"]


def test_handle_jsonrpc_tools_list() -> None:
    servers = [FakeServer("Weather", ["forecast"])]
    response = handle_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, servers)
    names = [t["name"] for t in response["result"]["tools"]]
    assert names == ["weather__forecast"]


def test_handle_jsonrpc_unknown_method() -> None:
    response = handle_jsonrpc({"jsonrpc": "2.0", "id": 3, "method": "prompts/list"}, [])
    assert response["error"]["code"] == -32601


def test_resolve_unqualified_unique_tool() -> None:
    servers = [FakeServer("Weather", ["forecast"]), FakeServer("Mail", ["send"])]
    target = resolve_tool_target(servers, "forecast")
    assert target is not None
    assert target[0].name == "Weather"
    assert target[1] == "forecast"
