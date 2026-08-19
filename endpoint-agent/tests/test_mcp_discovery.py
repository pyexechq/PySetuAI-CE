"""Unit tests for endpoint agent MCP server discovery."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pysetu_agent.discovery import discover_mcp_servers


class DiscoverMcpServersTest(unittest.TestCase):
    def test_empty_when_no_configs(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            servers = discover_mcp_servers(home=home)
            self.assertEqual(servers, [])

    def test_discovers_project_mcp_json(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            Path(home, ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "github": {
                                "command": "npx",
                                "args": ["-y", "@modelcontextprotocol/server-github"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            servers = discover_mcp_servers(home=home)
            self.assertEqual(len(servers), 1)
            self.assertEqual(servers[0].name, "github")
            self.assertEqual(servers[0].command, "npx")
            self.assertEqual(servers[0].transport, "stdio")

    def test_discovers_http_server(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            Path(home, ".cursor").mkdir(parents=True)
            Path(home, ".cursor", "mcp.json").write_text(
                json.dumps({"mcpServers": {"jira": {"url": "https://mcp.example.com/jira"}}}),
                encoding="utf-8",
            )
            servers = discover_mcp_servers(home=home)
            self.assertEqual(len(servers), 1)
            self.assertEqual(servers[0].name, "jira")
            self.assertEqual(servers[0].url, "https://mcp.example.com/jira")
            self.assertEqual(servers[0].transport, "http")

    def test_discovers_claude_desktop_config(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            config_dir = Path(home, ".config", "claude")
            config_dir.mkdir(parents=True)
            Path(config_dir, "claude_desktop_config.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "filesystem": {
                                "command": "npx",
                                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            servers = discover_mcp_servers(home=home)
            self.assertEqual(len(servers), 1)
            self.assertEqual(servers[0].name, "filesystem")

    def test_dedupes_same_name_across_sources(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            Path(home, ".mcp.json").write_text(
                json.dumps({"mcpServers": {"github": {"command": "npx"}}}),
                encoding="utf-8",
            )
            Path(home, ".cursor").mkdir()
            Path(home, ".cursor", "mcp.json").write_text(
                json.dumps({"mcpServers": {"github": {"command": "npx"}}}),
                encoding="utf-8",
            )
            servers = discover_mcp_servers(home=home)
            self.assertEqual(len(servers), 1)

    def test_ignores_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            Path(home, ".mcp.json").write_text("not json", encoding="utf-8")
            servers = discover_mcp_servers(home=home)
            self.assertEqual(servers, [])

    def test_parses_tools_list(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            Path(home, ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "github": {
                                "command": "npx",
                                "tools": ["searchRepositories", "createIssue"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            servers = discover_mcp_servers(home=home)
            self.assertEqual(servers[0].tools, ("searchRepositories", "createIssue"))


if __name__ == "__main__":
    unittest.main()
