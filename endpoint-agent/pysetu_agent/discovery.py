"""AI tool discovery for the endpoint agent.

Detection is filesystem-based and intentionally lightweight: binaries on PATH,
well-known configuration directories, and installed VS Code extensions. This
keeps the agent dependency-free and unit-testable without a live machine.
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass


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
