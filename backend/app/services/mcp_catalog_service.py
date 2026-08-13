"""Curated MCP catalog and install specs (BL-066 / S12-02)."""

from __future__ import annotations

from typing import Any

CATALOG_ENTRIES: list[dict[str, Any]] = [
    {
        "slug": "github",
        "name": "GitHub",
        "description": "Repos, issues, pull requests, and code search via the GitHub MCP server.",
        "category": "Developer",
        "transport": "sse",
        "default_endpoint": "https://api.githubcopilot.com/mcp/",
        "tool_names": ["search_code", "list_issues", "create_issue", "get_file"],
        "auth_required": True,
        "vendor": "GitHub",
    },
    {
        "slug": "filesystem",
        "name": "Filesystem",
        "description": "Read and write files on a configured workspace path.",
        "category": "Local",
        "transport": "stdio",
        "default_endpoint": None,
        "tool_names": ["read_file", "write_file", "list_directory"],
        "auth_required": False,
        "vendor": "Anthropic",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
    },
    {
        "slug": "postgres",
        "name": "PostgreSQL",
        "description": "Query and inspect PostgreSQL schemas with read-oriented tools.",
        "category": "Data",
        "transport": "stdio",
        "default_endpoint": None,
        "tool_names": ["query", "list_tables", "describe_table"],
        "auth_required": True,
        "vendor": "Anthropic",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
    },
    {
        "slug": "slack",
        "name": "Slack",
        "description": "Search channels and post messages through a Slack MCP connector.",
        "category": "Collaboration",
        "transport": "sse",
        "default_endpoint": "https://mcp.slack.com/sse",
        "tool_names": ["search_messages", "list_channels", "post_message"],
        "auth_required": True,
        "vendor": "Slack",
    },
    {
        "slug": "fetch",
        "name": "Fetch",
        "description": "HTTP fetch for public URLs. Governed by tenant URL allow/deny lists and vendor hooks.",
        "category": "Web",
        "transport": "sse",
        "default_endpoint": "https://mcp.fetch.local/sse",
        "tool_names": ["fetch"],
        "auth_required": False,
        "vendor": "MCP",
    },
    {
        "slug": "memory",
        "name": "Memory",
        "description": "Persistent knowledge graph memory for agents.",
        "category": "Knowledge",
        "transport": "stdio",
        "default_endpoint": None,
        "tool_names": ["create_entities", "search_nodes", "add_observations"],
        "auth_required": False,
        "vendor": "Anthropic",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
    },
    {
        "slug": "brave-search",
        "name": "Brave Search",
        "description": "Web search via Brave. Use with URL allow/deny lists for enterprise.",
        "category": "Web",
        "transport": "stdio",
        "default_endpoint": None,
        "tool_names": ["brave_web_search", "brave_local_search"],
        "auth_required": True,
        "vendor": "Brave",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    },
    {
        "slug": "notion",
        "name": "Notion",
        "description": "Search and update Notion pages and databases.",
        "category": "Knowledge",
        "transport": "sse",
        "default_endpoint": "https://mcp.notion.com/sse",
        "tool_names": ["search", "get_page", "create_page"],
        "auth_required": True,
        "vendor": "Notion",
    },
]


def list_catalog_entries() -> list[dict[str, Any]]:
    return [dict(entry) for entry in CATALOG_ENTRIES]


def get_catalog_entry(slug: str) -> dict[str, Any] | None:
    key = (slug or "").strip().lower()
    for entry in CATALOG_ENTRIES:
        if entry["slug"] == key:
            return dict(entry)
    return None


def catalog_slug_installed(servers: list[Any], slug: str) -> bool:
    key = (slug or "").strip().lower()
    for server in servers:
        config = getattr(server, "connection_config", None) or {}
        if isinstance(config, dict) and str(config.get("catalog_slug", "")).lower() == key:
            return True
    return False


def _connection_config_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    config: dict[str, Any] = {"catalog_slug": entry["slug"]}
    command = entry.get("command")
    if isinstance(command, str) and command.strip():
        config["command"] = command.strip()
    args = entry.get("args")
    if isinstance(args, list):
        config["args"] = [str(item) for item in args]
    return config


def install_spec_from_entry(
    entry: dict[str, Any],
    *,
    endpoint_url: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    url = (endpoint_url or "").strip() or entry.get("default_endpoint")
    return {
        "name": (name or entry["name"]).strip(),
        "category": entry["category"],
        "status": "offline",
        "tool_names": list(entry.get("tool_names") or []),
        "endpoint_url": url,
        "transport": entry["transport"],
        "connection_config": _connection_config_from_entry(entry),
    }


def custom_install_spec(
    *,
    name: str,
    endpoint_url: str,
    transport: str = "sse",
    category: str = "Custom",
) -> dict[str, Any]:
    url = endpoint_url.strip()
    if not url:
        raise ValueError("Transport URL is required")
    label = name.strip()
    if not label:
        raise ValueError("Server name is required")
    mode = transport.strip().lower() or "sse"
    return {
        "name": label,
        "category": category.strip() or "Custom",
        "status": "offline",
        "tool_names": [],
        "endpoint_url": url,
        "transport": mode,
        "connection_config": {"catalog_slug": "custom"},
    }
