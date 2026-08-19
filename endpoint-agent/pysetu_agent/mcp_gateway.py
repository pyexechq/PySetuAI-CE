"""Local MCP gateway that intercepts tool-call traffic for AI desktop clients.

Claude Code, Claude Desktop, Cursor, and VSCode all connect to MCP servers over
stdio. This gateway sits between the tool and a real MCP server: the tool is
pointed at the gateway as if it were an MCP server, and the gateway spawns the
real server as a subprocess and forwards JSON-RPC messages. Every ``tools/call``
is scanned for secrets/PII and either blocked, redacted, or passed through.

MCP stdio uses newline-delimited JSON-RPC 2.0 (one JSON object per line).
HTTP/SSE uses ``Content-Length`` framing; helpers are provided for future use.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable

from .detection import ScanResult, detect
from .discovery import DiscoveredMcpServer
from .policy import LocalPolicy, evaluate


# ---------------------------------------------------------------------------
# JSON-RPC framing (newline-delimited stdio)
# ---------------------------------------------------------------------------

def read_message(stream) -> dict | None:
    """Read one newline-delimited JSON-RPC message. Returns None on EOF."""
    for line in stream:
        line = line.strip()
        if not line:
            continue
        return json.loads(line)
    return None


def write_message(stream, message: dict) -> None:
    """Write one newline-delimited JSON-RPC message."""
    stream.write(json.dumps(message) + "\n")
    stream.flush()


# ---------------------------------------------------------------------------
# JSON-RPC framing (Content-Length, HTTP/SSE)
# ---------------------------------------------------------------------------

def read_http_message(stream) -> dict | None:
    """Read a Content-Length framed JSON-RPC message (HTTP/SSE)."""
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = stream.read(length)
    return json.loads(body)


def write_http_message(stream, message: dict) -> None:
    """Write a Content-Length framed JSON-RPC message."""
    body = json.dumps(message)
    stream.write(f"Content-Length: {len(body)}\r\n\r\n{body}")
    stream.flush()


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GatewayDecision:
    action: str  # "block" | "redact" | "allow"
    reason: str
    redacted_arguments: dict | None = None
    classifications: list[str] = field(default_factory=list)


def decide_tool_call(
    server_name: str,
    tool_name: str,
    arguments: dict,
    policy: LocalPolicy,
    *,
    detector: Callable[[str], ScanResult] = detect,
) -> GatewayDecision:
    """Scan tool arguments and decide block/redact/allow."""
    serialized = json.dumps(arguments, sort_keys=True)
    result = detector(serialized)
    if not result.has_sensitive:
        return GatewayDecision(action="allow", reason="No sensitive data detected")

    resource = f"mcp://{server_name}/{tool_name}"
    decision = evaluate(policy, resource, result.classifications)
    if decision == "block":
        return GatewayDecision(
            action="block",
            reason="Sensitive data in tool arguments",
            classifications=result.classifications,
        )
    if decision == "redact" and result.redacted_content is not None:
        try:
            redacted = json.loads(result.redacted_content)
        except (ValueError, TypeError):
            # Redaction produced invalid JSON (e.g. a numeric value became
            # [REDACTED]); never forward malformed args.
            return GatewayDecision(
                action="block",
                reason="Redaction would produce invalid tool arguments",
                classifications=result.classifications,
            )
        return GatewayDecision(
            action="redact",
            reason="Redacted sensitive data in tool arguments",
            redacted_arguments=redacted,
            classifications=result.classifications,
        )
    return GatewayDecision(action="allow", reason="No sensitive data detected")


# ---------------------------------------------------------------------------
# Upstream server process
# ---------------------------------------------------------------------------

class McpServerProcess:
    """Spawned real MCP server over stdio. Injectable via ``popen``."""

    def __init__(self, server: DiscoveredMcpServer, *, popen: Callable = subprocess.Popen) -> None:
        self.server = server
        self._popen = popen
        self._proc = None

    def start(self) -> None:
        command = [self.server.command, *self.server.args]
        self._proc = self._popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )

    def write(self, message: dict) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("server not started")
        write_message(self._proc.stdin, message)

    def read(self) -> dict | None:
        if self._proc is None or self._proc.stdout is None:
            raise RuntimeError("server not started")
        return read_message(self._proc.stdout)

    def stop(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()


# ---------------------------------------------------------------------------
# Message handling (the proxy core)
# ---------------------------------------------------------------------------

def jsonrpc_error(request_id, code: int, message_text: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message_text},
    }


def handle_tool_call(
    message: dict,
    server: DiscoveredMcpServer,
    policy: LocalPolicy,
    upstream,
    *,
    detector: Callable[[str], ScanResult] = detect,
) -> dict:
    """Intercept tools/call. Returns the response to write back to the tool."""
    params = message.get("params") or {}
    tool_name = params.get("name", "")
    arguments = params.get("arguments") or {}
    request_id = message.get("id")

    decision = decide_tool_call(server.name, tool_name, arguments, policy, detector=detector)
    if decision.action == "block":
        return jsonrpc_error(request_id, -32000, f"blocked by PySetu policy: {decision.reason}")

    if decision.action == "redact" and decision.redacted_arguments is not None:
        params = dict(params)
        params["arguments"] = decision.redacted_arguments
        message = dict(message)
        message["params"] = params

    upstream.write(message)
    return upstream.read()


def handle_message(
    message: dict,
    server: DiscoveredMcpServer,
    policy: LocalPolicy,
    upstream,
    *,
    detector: Callable[[str], ScanResult] = detect,
) -> dict | None:
    """Route one client message. Returns a response to write, or None for notifications."""
    method = message.get("method")
    if method == "tools/call":
        return handle_tool_call(message, server, policy, upstream, detector=detector)

    upstream.write(message)
    if "id" in message:
        return upstream.read()
    return None


def run_gateway(
    server: DiscoveredMcpServer,
    policy: LocalPolicy,
    *,
    reader=None,
    writer=None,
    server_factory: Callable = McpServerProcess,
    detector: Callable[[str], ScanResult] = detect,
) -> int:
    """Proxy loop: read client message -> handle -> write response. Returns 0."""
    reader = reader if reader is not None else sys.stdin
    writer = writer if writer is not None else sys.stdout

    upstream = server_factory(server)
    upstream.start()
    try:
        while True:
            message = read_message(reader)
            if message is None:
                break
            response = handle_message(message, server, policy, upstream, detector=detector)
            if response is not None:
                write_message(writer, response)
    finally:
        upstream.stop()
    return 0


# ---------------------------------------------------------------------------
# Config generation
# ---------------------------------------------------------------------------

def gateway_config(
    servers: list[DiscoveredMcpServer],
    *,
    launcher: str | None = None,
) -> dict:
    """Build an MCP config mapping each stdio server to a gateway entry."""
    launcher = launcher if launcher is not None else sys.executable
    entries: dict[str, dict] = {}
    for server in servers:
        if server.transport != "stdio" or not server.command:
            continue
        entries[server.name] = {
            "command": launcher,
            "args": ["-m", "pysetu_agent", "--mcp-gateway", "--server", server.name],
        }
    return {"mcpServers": entries}


def write_gateway_config(path: str, servers: list[DiscoveredMcpServer], *, launcher: str | None = None) -> str:
    """Write gateway_config to ``path`` as indented JSON. Returns path."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(gateway_config(servers, launcher=launcher), handle, indent=2)
    return path
