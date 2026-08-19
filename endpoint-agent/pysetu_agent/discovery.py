"""AI tool discovery for the endpoint agent.

Detection is filesystem-based and intentionally lightweight: binaries on PATH,
well-known configuration directories, installed VS Code extensions, and MCP
server configs. This keeps the agent dependency-free and unit-testable without
a live machine.
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiscoveredTool:
    name: str
    agent_type: str
    vendor: str
    version: str = ""
    confidence: str = "high"
    source: str = "binary"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    agent_type: str
    vendor: str
    binaries: tuple[str, ...] = ()
    config_dirs: tuple[str, ...] = ()
    extension_globs: tuple[str, ...] = ()


TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec("Claude Code", "coding_agent", "Anthropic", binaries=("claude",), config_dirs=(".claude", ".claude.json")),
    ToolSpec("Cursor", "ide_copilot", "Anysphere", binaries=("cursor",), config_dirs=(".cursor",)),
    ToolSpec("Windsurf", "ide_copilot", "Codeium", binaries=("windsurf",), config_dirs=(".windsurf", ".config/windsurf")),
    ToolSpec("Ollama", "local_llm_agent", "Ollama", binaries=("ollama",), config_dirs=(".ollama",)),
    ToolSpec("GitHub Copilot", "ide_copilot", "GitHub", extension_globs=("github.copilot-*",)),
    ToolSpec("Cline", "coding_agent", "Cline", extension_globs=("saoudrizwan.claude-dev-*",)),
    ToolSpec("Roo Code", "coding_agent", "Roo Code", extension_globs=("rooveterinaryinc.roo-cline-*",)),
    ToolSpec("Continue", "ide_copilot", "Continue", extension_globs=("continue.continue-*",)),
)


def default_extensions_dir(home: str) -> str:
    return os.path.join(home, ".vscode", "extensions")


def binary_exists(name: str, path_entries: list[str]) -> bool:
    for entry in path_entries:
        if not entry:
            continue
        candidate = os.path.join(entry, name)
        if os.path.isfile(candidate):
            return True
        if os.name == "nt" and os.path.isfile(candidate + ".exe"):
            return True
    return False


def discover_tools(
    *,
    home: str | None = None,
    path_entries: list[str] | None = None,
    extensions_dir: str | None = None,
) -> list[DiscoveredTool]:
    """Return discovered AI tools.

    All inputs are injectable so the function is testable without touching the
    real host environment.
    """
    home = home if home is not None else os.path.expanduser("~")
    path_entries = path_entries if path_entries is not None else os.environ.get("PATH", "").split(os.pathsep)
    extensions_dir = extensions_dir if extensions_dir is not None else default_extensions_dir(home)

    found: list[DiscoveredTool] = []
    for spec in TOOL_SPECS:
        source: str | None = None
        confidence = "high"

        for binary in spec.binaries:
            if binary_exists(binary, path_entries):
                source = "binary"
                break

        if source is None:
            for dir_name in spec.config_dirs:
                if os.path.exists(os.path.join(home, dir_name)):
                    source = "config"
                    break

        if source is None:
            for pattern in spec.extension_globs:
                if glob.glob(os.path.join(extensions_dir, pattern)):
                    source = "extension"
                    break

        if source is not None:
            found.append(
                DiscoveredTool(
                    name=spec.name,
                    agent_type=spec.agent_type,
                    vendor=spec.vendor,
                    confidence=confidence,
                    source=source,
                )
            )
    return found


@dataclass(frozen=True)
class DiscoveredMcpServer:
    name: str
    source: str
    command: str = ""
    url: str = ""
    transport: str = "stdio"
    tools: tuple[str, ...] = field(default_factory=tuple)


def _mcp_server_name(server_id: str, server: dict) -> str:
    return str(server.get("name") or server_id)


def _mcp_server_command(server: dict) -> str:
    command = server.get("command")
    if isinstance(command, str):
        return command
    if isinstance(command, list) and command:
        return str(command[0])
    return ""


def _mcp_server_url(server: dict) -> str:
    url = server.get("url")
    return str(url) if isinstance(url, str) else ""


def _mcp_server_tools(server: dict) -> tuple[str, ...]:
    tools = server.get("tools")
    if isinstance(tools, list):
        return tuple(str(tool) for tool in tools if isinstance(tool, str))
    return ()


def _parse_mcp_servers(servers: dict, source: str) -> list[DiscoveredMcpServer]:
    found: list[DiscoveredMcpServer] = []
    for server_id, server in servers.items():
        if not isinstance(server, dict):
            continue
        command = _mcp_server_command(server)
        url = _mcp_server_url(server)
        found.append(
            DiscoveredMcpServer(
                name=_mcp_server_name(server_id, server),
                source=source,
                command=command,
                url=url,
                transport="http" if url else "stdio",
                tools=_mcp_server_tools(server),
            )
        )
    return found


def _mcp_servers_from_file(path: str) -> list[DiscoveredMcpServer]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    servers = data.get("mcpServers")
    if isinstance(servers, dict):
        return _parse_mcp_servers(servers, path)
    return []


def discover_mcp_servers(*, home: str | None = None) -> list[DiscoveredMcpServer]:
    """Discover MCP server configs from well-known locations.

    Scans project-level ``.mcp.json``, Cursor's ``.cursor/mcp.json``, and the
    Claude Desktop config. All inputs are injectable so the function is testable
    without touching the real host environment.
    """
    home = home if home is not None else os.path.expanduser("~")
    candidates: list[str] = [
        os.path.join(home, ".mcp.json"),
        os.path.join(home, ".cursor", "mcp.json"),
        os.path.join(home, ".config", "claude", "claude_desktop_config.json"),
        os.path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json"),
    ]
    found: list[DiscoveredMcpServer] = []
    seen: set[str] = set()
    for path in candidates:
        for server in _mcp_servers_from_file(path):
            if server.name in seen:
                continue
            seen.add(server.name)
            found.append(server)
    return found
