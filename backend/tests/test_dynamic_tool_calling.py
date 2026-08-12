"""Tests for dynamic MCP tool ranking (BL-064 / S11-03)."""

from app.services.dynamic_tool_service import (
    catalog_from_servers,
    rank_and_filter_tools,
    resolve_dynamic_tool_config,
    tool_token_estimate,
)


def _tool(name: str, description: str = "", schema: dict | None = None) -> dict:
    return {"name": name, "description": description, "inputSchema": schema or {"type": "object"}}


def test_rank_and_filter_caps_at_max_tools() -> None:
    tools = [_tool(f"tool_{i}", f"utility helper {i}") for i in range(20)]
    result = rank_and_filter_tools("please help", tools, max_tools=5)
    assert result.enabled is True
    assert len(result.selected) <= 5
    assert result.catalog_count == 20
    assert result.selected_count == 5


def test_rank_and_filter_prefers_query_relevant_tools() -> None:
    tools = [
        _tool("calendar_list", "List calendar events for a user"),
        _tool("weather_forecast", "Get the weather forecast for a city"),
        _tool("jira_create_issue", "Create a Jira ticket in a project"),
        _tool("slack_send", "Send a Slack message to a channel"),
    ]
    result = rank_and_filter_tools("What is the weather in Mumbai tomorrow?", tools, max_tools=2)
    names = [t["name"] for t in result.selected]
    assert "weather_forecast" in names
    assert "jira_create_issue" not in names


def test_rank_and_filter_reports_token_kpi() -> None:
    tools = [_tool(f"search_{i}", "Search documents " * 20) for i in range(10)]
    result = rank_and_filter_tools("search documents", tools, max_tools=2)
    assert result.original_tokens > result.compressed_tokens
    assert result.tokens_saved > 0
    assert result.savings_pct >= 50.0


def test_rank_and_filter_disabled_returns_passthrough() -> None:
    tools = [_tool("a"), _tool("b"), _tool("c")]
    result = rank_and_filter_tools("hello", tools, max_tools=1, enabled=False)
    assert result.enabled is False
    assert result.selected == tools
    assert result.tokens_saved == 0


def test_catalog_from_servers_uses_schemas_then_names() -> None:
    class FakeServer:
        def __init__(self, name, tool_names, connection_config):
            self.name = name
            self.tool_names = tool_names
            self.connection_config = connection_config

    servers = [
        FakeServer(
            "docs",
            ["search"],
            {"tool_schemas": [{"name": "search", "description": "Find files", "inputSchema": {"type": "object"}}]},
        ),
        FakeServer("mail", ["send_email"], {}),
    ]
    catalog = catalog_from_servers(servers)
    assert len(catalog) == 2
    assert catalog[0]["name"] == "search"
    assert catalog[0]["description"] == "Find files"
    assert catalog[1]["name"] == "send_email"


def test_resolve_dynamic_tool_config_request_override() -> None:
    enabled, max_tools = resolve_dynamic_tool_config(
        tenant_enabled=False,
        tenant_max_tools=8,
        request_metadata={"dynamic_tool_calling": True, "dynamic_tool_max": 3},
    )
    assert enabled is True
    assert max_tools == 3


def test_tool_token_estimate_grows_with_description() -> None:
    short = tool_token_estimate([_tool("a", "hi")])
    long = tool_token_estimate([_tool("a", "hi " * 200)])
    assert long > short
