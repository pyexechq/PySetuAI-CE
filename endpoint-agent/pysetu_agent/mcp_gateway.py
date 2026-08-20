"""Local MCP gateway that intercepts tool-call traffic for AI desktop clients.

Claude Code, Claude Desktop, Cursor, and VSCode all connect to MCP servers over
stdio. This gateway sits between the tool and a real MCP server: the tool is
pointed at the gateway as if it were an MCP server, and the gateway spawns the
real server as a subprocess and forwards JSON-RPC messages. Every ``tools/call``
is scanned for secrets/PII and either blocked, redacted, or passed through.
Tool *responses* are scanned too, so sensitive data returned by a tool (e.g. an
HR database query) is redacted before it reaches the client.

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


@dataclass(frozen=True)
class ResponseDecision:
    action: str  # "block" | "redact" | "allow"
    reason: str
    redacted_result: dict | None = None
    classifications: list[str] = field(default_factory=list)


def _text_blocks(result: dict) -> list[tuple[dict, str, str]]:
    """Return (container, key, text) for each redactable text block in an MCP result.

    MCP ``tools/call`` results carry ``content`` as a list of blocks. Text lives
    in ``{type: text, text: ...}`` blocks and in ``{type: resource, resource:
    {text: ...}}`` blocks. Each returned tuple lets the caller rewrite the text
    in place on a deep copy.
    """
    blocks: list[tuple[dict, str, str]] = []
    content = result.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                blocks.append((block, "text", block["text"]))
            elif isinstance(block, dict) and block.get("type") == "resource":
                resource = block.get("resource")
                if isinstance(resource, dict) and isinstance(resource.get("text"), str):
                    blocks.append((resource, "text", resource["text"]))
    return blocks


def decide_tool_response(
    server_name: str,
    tool_name: str,
    result: dict,
    policy: LocalPolicy,
    *,
    detector: Callable[[str], ScanResult] = detect,
) -> ResponseDecision:
    """Scan tool response text and decide block/redact/allow.

    Unlike arguments, a response has already left the server, so redaction is
    the primary mechanism; ``block`` is returned only when the policy resolves
    to block for the tool's resource path.
    """
    blocks = _text_blocks(result)
    if not blocks:
        return ResponseDecision(action="allow", reason="No text content in response")

    redacted_result = json.loads(json.dumps(result))
    redacted_blocks = _text_blocks(redacted_result)

    all_classifications: list[str] = []
    any_redacted = False
    for (container, key, text), (redacted_container, redacted_key, _) in zip(blocks, redacted_blocks):
        scan = detector(text)
        if not scan.has_sensitive:
            continue
        all_classifications.extend(scan.classifications)
        if scan.redacted_content is not None:
            redacted_container[redacted_key] = scan.redacted_content
            any_redacted = True

    if not all_classifications:
        return ResponseDecision(action="allow", reason="No sensitive data in response")

    resource = f"mcp://{server_name}/{tool_name}"
    decision = evaluate(policy, resource, all_classifications)
    if decision == "block":
        return ResponseDecision(
            action="block",
            reason="Sensitive data in tool response",
            classifications=all_classifications,
        )
    if decision == "redact" and any_redacted:
        return ResponseDecision(
            action="redact",
            reason="Redacted sensitive data in tool response",
            redacted_result=redacted_result,
            classifications=all_classifications,
        )
    return ResponseDecision(action="allow", reason="No sensitive data detected")


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
    redact_responses: bool = True,
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
    response = upstream.read()

    if redact_responses and response is not None and isinstance(response, dict):
        result = response.get("result")
        if isinstance(result, dict):
            response_decision = decide_tool_response(
                server.name, tool_name, result, policy, detector=detector
            )
            if response_decision.action == "block":
                return jsonrpc_error(
                    request_id, -32000, f"blocked by PySetu policy: {response_decision.reason}"
                )
            if response_decision.action == "redact" and response_decision.redacted_result is not None:
                response = dict(response)
                response["result"] = response_decision.redacted_result

    return response


def handle_message(
    message: dict,
    server: DiscoveredMcpServer,
    policy: LocalPolicy,
    upstream,
    *,
    detector: Callable[[str], ScanResult] = detect,
    redact_responses: bool = True,
) -> dict | None:
    """Route one client message. Returns a response to write, or None for notifications."""
    method = message.get("method")
    if method == "tools/call":
        return handle_tool_call(
            message, server, policy, upstream, detector=detector, redact_responses=redact_responses
        )

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
    redact_responses: bool = True,
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
            response = handle_message(
                message, server, policy, upstream, detector=detector, redact_responses=redact_responses
            )
            if response is not None:
                write_message(writer, response)
    finally:
        upstream.stop()
    return 0


# ---------------------------------------------------------------------------
# Multiplexing (single process, multiple upstream servers)
# ---------------------------------------------------------------------------

class McpServerPool:
    """Manage multiple upstream MCP server processes, keyed by server name."""

    def __init__(self, servers: list[DiscoveredMcpServer], *, server_factory: Callable = McpServerProcess) -> None:
        self._servers = {server.name: server for server in servers}
        self._procs = {server.name: server_factory(server) for server in servers}
        self._order = [server.name for server in servers]

    def start(self) -> None:
        for proc in self._procs.values():
            proc.start()

    def get(self, name: str):
        return self._procs.get(name)

    def server(self, name: str) -> DiscoveredMcpServer | None:
        return self._servers.get(name)

    def default_name(self) -> str | None:
        return self._order[0] if self._order else None

    def names(self) -> list[str]:
        return list(self._order)

    def stop(self) -> None:
        for proc in self._procs.values():
            proc.stop()


def run_multiplex_gateway(
    servers: list[DiscoveredMcpServer],
    policy: LocalPolicy,
    *,
    reader=None,
    writer=None,
    server_factory: Callable = McpServerProcess,
    detector: Callable[[str], ScanResult] = detect,
    redact_responses: bool = True,
) -> int:
    """Proxy loop for multiple servers in one process.

    Each incoming message is routed to the upstream named by its ``server``
    field (a PySetu extension to the JSON-RPC envelope). Messages without a
    ``server`` field route to the first server. Returns 0.
    """
    reader = reader if reader is not None else sys.stdin
    writer = writer if writer is not None else sys.stdout

    pool = McpServerPool(servers, server_factory=server_factory)
    pool.start()
    try:
        while True:
            message = read_message(reader)
            if message is None:
                break
            server_name = message.get("server") or pool.default_name()
            upstream = pool.get(server_name) if server_name else None
            server = pool.server(server_name) if server_name else None
            if upstream is None or server is None:
                response = jsonrpc_error(message.get("id"), -32000, f"unknown MCP server: {server_name}")
            else:
                response = handle_message(
                    message,
                    server,
                    policy,
                    upstream,
                    detector=detector,
                    redact_responses=redact_responses,
                )
            if response is not None:
                write_message(writer, response)
    finally:
        pool.stop()
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
