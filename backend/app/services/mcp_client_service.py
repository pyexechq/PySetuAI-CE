"""MCP JSON-RPC client for sessions, initialization, and tool discovery."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.models.governance import MCPServer
from app.services.mcp_transport import build_mcp_headers, resolve_timeout_sec
from app.services.mcp_trust_scoring_service import record_mcp_invoke_outcome, refresh_mcp_trust_scores

MCP_PROTOCOL_VERSION = "2024-11-05"
SESSION_TTL_SEC = 1800


@dataclass
class McpDiscoverResult:
    ok: bool
    tool_names: list[str]
    message: str
    latency_ms: int = 0
    skipped: bool = False
    session: dict | None = None
    tool_schemas: list[dict] | None = None


@dataclass
class McpToolInvokeResult:
    ok: bool
    message: str
    result: dict | None = None
    latency_ms: int = 0
    session: dict | None = None
    skipped: bool = False


class McpClientError(Exception):
    pass


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def session_is_active(session: dict | None) -> bool:
    if not session or session.get("state") != "initialized":
        return False
    reference = _parse_timestamp(session.get("last_used_at")) or _parse_timestamp(session.get("initialized_at"))
    if reference is None:
        return False
    age = (datetime.now(UTC) - reference.astimezone(UTC)).total_seconds()
    return age < SESSION_TTL_SEC


def touch_session(session: dict, *, reused: bool) -> dict:
    updated = dict(session)
    updated["last_used_at"] = datetime.now(UTC).isoformat()
    updated["reused"] = reused
    return updated


async def _jsonrpc(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    request_id: int,
    method: str,
    params: dict | None = None,
) -> dict:
    payload: dict = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    response = await client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise McpClientError("Invalid JSON-RPC response")
    if data.get("error"):
        error = data["error"]
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise McpClientError(message or "JSON-RPC error")
    result = data.get("result")
    return result if isinstance(result, dict) else {}


async def _jsonrpc_notification(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    method: str,
    params: dict | None = None,
) -> None:
    payload: dict = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        payload["params"] = params
    response = await client.post(url, headers=headers, json=payload)
    response.raise_for_status()


async def establish_mcp_session(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
) -> dict:
    session_id = str(uuid.uuid4())
    init_result = await _jsonrpc(
        client,
        url,
        headers,
        1,
        "initialize",
        {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "pysetu", "version": "1.0"},
        },
    )
    await _jsonrpc_notification(client, url, headers, "notifications/initialized")
    return touch_session(
        {
            "state": "initialized",
            "session_id": session_id,
            "initialized_at": datetime.now(UTC).isoformat(),
            "protocol_version": init_result.get("protocolVersion", MCP_PROTOCOL_VERSION),
            "server_info": init_result.get("serverInfo"),
            "capabilities": init_result.get("capabilities"),
        },
        reused=False,
    )


async def ensure_mcp_session(
    client: httpx.AsyncClient,
    server: MCPServer,
    endpoint: str,
    headers: dict[str, str],
) -> tuple[dict, bool]:
    existing = (server.connection_config or {}).get("mcp_session")
    if session_is_active(existing):
        return touch_session(existing, reused=True), True

    session = await establish_mcp_session(client, endpoint, headers)
    return session, False


async def discover_mcp_tools(server: MCPServer, access_token: str | None = None) -> McpDiscoverResult:
    transport = (server.transport or "sse").strip().lower()
    if transport == "stdio":
        return McpDiscoverResult(
            ok=True,
            tool_names=list(server.tool_names or []),
            message="Stdio transport uses a local MCP agent; remote tool discovery skipped.",
            skipped=True,
        )
    if transport == "rest_proxy":
        from app.services.mcp_rest_proxy_service import discover_rest_tools

        tools = discover_rest_tools(server)
        if not tools:
            return McpDiscoverResult(
                ok=False,
                tool_names=[],
                message="No REST spec stored for this server.",
            )
        return McpDiscoverResult(
            ok=True,
            tool_names=[t["name"] for t in tools],
            message=f"REST proxy: {len(tools)} tool(s) from spec.",
            tool_schemas=tools,
        )

    endpoint = (server.endpoint_url or "").strip()
    if not endpoint:
        return McpDiscoverResult(
            ok=False,
            tool_names=[],
            message="No endpoint URL configured for this server.",
        )

    timeout_sec = resolve_timeout_sec(server.connection_config)
    headers = build_mcp_headers(server.connection_config, json_rpc=True, access_token=access_token)
    started = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            session, reused = await ensure_mcp_session(client, server, endpoint, headers)
            tools_result = await _jsonrpc(client, endpoint, headers, 2, "tools/list", {})
            latency_ms = max(1, int((time.perf_counter() - started) * 1000))

            raw_tools = tools_result.get("tools", [])
            tool_names: list[str] = []
            tool_schemas: list[dict] = []
            if isinstance(raw_tools, list):
                for tool in raw_tools:
                    if isinstance(tool, dict) and tool.get("name"):
                        name = str(tool["name"])
                        tool_names.append(name)
                        tool_schemas.append(
                            {
                                "name": name,
                                "description": tool.get("description"),
                                "inputSchema": tool.get("inputSchema") or tool.get("input_schema"),
                            }
                        )

            prefix = "Reused MCP session;" if reused else "MCP session established;"
            if not tool_names:
                return McpDiscoverResult(
                    ok=False,
                    tool_names=[],
                    message=f"{prefix} no tools were returned by tools/list.",
                    latency_ms=latency_ms,
                    session=session,
                )

            return McpDiscoverResult(
                ok=True,
                tool_names=tool_names,
                message=f"{prefix} discovered {len(tool_names)} tool(s).",
                latency_ms=latency_ms,
                session=session,
                tool_schemas=tool_schemas,
            )
    except httpx.TimeoutException:
        return McpDiscoverResult(
            ok=False,
            tool_names=[],
            message=f"Tool discovery timed out after {int(timeout_sec)}s.",
            latency_ms=int(timeout_sec * 1000),
        )
    except httpx.HTTPError as exc:
        return McpDiscoverResult(ok=False, tool_names=[], message=f"HTTP error: {exc}")
    except McpClientError as exc:
        return McpDiscoverResult(ok=False, tool_names=[], message=str(exc))


async def invoke_mcp_tool(
    server: MCPServer,
    tool_name: str,
    arguments: dict | None = None,
    access_token: str | None = None,
) -> McpToolInvokeResult:
    transport = (server.transport or "sse").strip().lower()
    if transport == "stdio":
        return McpToolInvokeResult(
            ok=False,
            message="Stdio transport uses a local MCP agent; remote tool invocation skipped.",
            skipped=True,
        )
    if transport == "rest_proxy":
        from app.services.mcp_rest_proxy_service import invoke_rest_tool

        started = time.perf_counter()
        ok, message, result = await invoke_rest_tool(server, tool_name, arguments, access_token=access_token)
        latency_ms = max(1, int((time.perf_counter() - started) * 1000))
        return McpToolInvokeResult(
            ok=ok,
            message=message,
            result=result,
            latency_ms=latency_ms,
        )

    endpoint = (server.endpoint_url or "").strip()
    if not endpoint:
        return McpToolInvokeResult(ok=False, message="No endpoint URL configured for this server.")

    trimmed_name = tool_name.strip()
    if not trimmed_name:
        return McpToolInvokeResult(ok=False, message="Tool name is required.")

    timeout_sec = resolve_timeout_sec(server.connection_config)
    headers = build_mcp_headers(server.connection_config, json_rpc=True, access_token=access_token)
    started = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            session, reused = await ensure_mcp_session(client, server, endpoint, headers)
            tool_result = await _jsonrpc(
                client,
                endpoint,
                headers,
                3,
                "tools/call",
                {"name": trimmed_name, "arguments": arguments or {}},
            )
            latency_ms = max(1, int((time.perf_counter() - started) * 1000))
            prefix = "Reused MCP session;" if reused else "MCP session established;"
            return McpToolInvokeResult(
                ok=True,
                message=f"{prefix} invoked {trimmed_name}.",
                result=tool_result,
                latency_ms=latency_ms,
                session=session,
            )
    except httpx.TimeoutException:
        return McpToolInvokeResult(
            ok=False,
            message=f"Tool invocation timed out after {int(timeout_sec)}s.",
            latency_ms=int(timeout_sec * 1000),
        )
    except httpx.HTTPError as exc:
        return McpToolInvokeResult(ok=False, message=f"HTTP error: {exc}")
    except McpClientError as exc:
        return McpToolInvokeResult(ok=False, message=str(exc))


def apply_discovered_tools(server: MCPServer, result: McpDiscoverResult) -> None:
    config = dict(server.connection_config or {})
    if result.session or result.tool_schemas:
        if result.session:
            config["mcp_session"] = result.session
        if result.tool_schemas:
            config["tool_schemas"] = result.tool_schemas
        server.connection_config = config

    if not result.ok or result.skipped:
        return

    server.tool_names = result.tool_names
    server.tools_count = len(result.tool_names)
    if result.latency_ms > 0:
        server.avg_latency_ms = result.latency_ms
    server.status = "healthy"
    refresh_mcp_trust_scores(server)


def apply_tool_invoke(server: MCPServer, result: McpToolInvokeResult) -> None:
    config = dict(server.connection_config or {})
    if result.session:
        config["mcp_session"] = result.session
        server.connection_config = config
    record_mcp_invoke_outcome(server, ok=result.ok, latency_ms=result.latency_ms or 0)
