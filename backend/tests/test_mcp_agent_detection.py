"""Tests for MCP agent auto-detection + per-agent toggles (BL-069 / S12-05)."""

from app.services.mcp_agent_service import (
    DEFAULT_AGENT_TOGGLES,
    detect_agent,
    filter_servers_for_agent,
    is_mcp_enabled_for_agent,
    merge_agent_toggles,
    server_allows_agent,
)


def test_detect_agent_from_metadata() -> None:
    assert detect_agent(None, {"agent": "claude"}) == "claude"
    assert detect_agent(None, {"client_agent": "openai"}) == "openai"


def test_detect_agent_from_user_agent() -> None:
    assert detect_agent("Claude-User anthropic-ai/0.1", None) == "claude"
    assert detect_agent("OpenAI/ChatGPT-Desktop", None) == "openai"
    assert detect_agent("Google-Gemini-CLI/1.0", None) == "gemini"
    assert detect_agent("Cursor/1.0", None) == "cursor"


def test_detect_agent_unknown_fallback() -> None:
    assert detect_agent("SomeCustomBot/1.0", None) == "unknown"


def test_is_mcp_enabled_for_agent() -> None:
    toggles = dict(DEFAULT_AGENT_TOGGLES)
    toggles["claude"] = False
    assert is_mcp_enabled_for_agent(toggles, "claude") is False
    assert is_mcp_enabled_for_agent(toggles, "openai") is True


class FakeServer:
    def __init__(self, name, connection_config=None):
        self.name = name
        self.connection_config = connection_config or {}


def test_filter_servers_respects_tenant_toggle() -> None:
    toggles = dict(DEFAULT_AGENT_TOGGLES)
    toggles["claude"] = False
    servers = [FakeServer("GitHub")]
    assert filter_servers_for_agent(servers, "claude", toggles) == []


def test_filter_servers_respects_per_server_allowlist() -> None:
    toggles = dict(DEFAULT_AGENT_TOGGLES)
    servers = [
        FakeServer("OpenAI Only", {"allowed_agents": ["openai"]}),
        FakeServer("Claude Only", {"allowed_agents": ["claude"]}),
    ]
    openai_only = filter_servers_for_agent(servers, "openai", toggles)
    assert [s.name for s in openai_only] == ["OpenAI Only"]
    claude_only = filter_servers_for_agent(servers, "claude", toggles)
    assert [s.name for s in claude_only] == ["Claude Only"]


def test_server_allows_agent_empty_allowlist() -> None:
    assert server_allows_agent(FakeServer("Any"), "gemini") is True


def test_merge_agent_toggles() -> None:
    merged = merge_agent_toggles(DEFAULT_AGENT_TOGGLES, {"claude": False, "cursor": True})
    assert merged["claude"] is False
    assert merged["openai"] is True
