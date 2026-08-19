"""Unit tests for endpoint agent tool discovery."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pysetu_agent.discovery import binary_exists, discover_tools


class BinaryExistsTest(unittest.TestCase):
    def test_found(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "claude").touch()
            self.assertTrue(binary_exists("claude", [directory]))

    def test_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(binary_exists("claude", [directory]))


class DiscoverToolsTest(unittest.TestCase):
    def test_detects_binary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "ollama").touch()
            tools = discover_tools(home="/nonexistent-home", path_entries=[directory], extensions_dir="/nonexistent")
            self.assertIn("Ollama", {tool.name for tool in tools})

    def test_detects_config_directory(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            Path(home, ".claude").mkdir()
            tools = discover_tools(home=home, path_entries=[], extensions_dir="/nonexistent")
            self.assertIn("Claude Code", {tool.name for tool in tools})

    def test_detects_vscode_extension(self) -> None:
        with tempfile.TemporaryDirectory() as extensions:
            Path(extensions, "github.copilot-1.2.3").mkdir()
            tools = discover_tools(home="/nonexistent-home", path_entries=[], extensions_dir=extensions)
            self.assertIn("GitHub Copilot", {tool.name for tool in tools})

    def test_empty_when_nothing_present(self) -> None:
        tools = discover_tools(home="/nonexistent-home", path_entries=[], extensions_dir="/nonexistent")
        self.assertEqual(tools, [])

    def test_tool_has_agent_type_and_vendor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "windsurf").touch()
            tools = discover_tools(home="/nonexistent-home", path_entries=[directory], extensions_dir="/nonexistent")
            self.assertEqual(len(tools), 1)
            self.assertEqual(tools[0].agent_type, "ide_copilot")
            self.assertEqual(tools[0].vendor, "Codeium")


if __name__ == "__main__":
    unittest.main()
