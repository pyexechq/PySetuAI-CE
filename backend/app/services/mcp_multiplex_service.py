"""MCP multiplex — one gateway URL for all tenant MCP servers (BL-065)."""

from __future__ import annotations

import re
from typing import Any, Awaitable, Callable

MCP_PROTOCOL_VERSION = "2024-11-05"
MULTIPLEX_SERVER_NAME = "pysetu-mcp-multiplex"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def server_slug(name: str) -> str:
    slug = _SLUG_RE.sub("_", (name or "").strip().lower()).strip("_")
    return slug or "server"


def qualify_tool_name(slug: str, tool_name: str) -> str:
    return f"{slug}__{tool_name}"


def parse_qualified_name(name: str) -> tuple[str | None, str]:
    if "__" in name:
        slug, tool = name.split("__", 1)
        return slug, tool
    return None, name


def resolve_tool_target(servers: list[Any], tool_name: str) -> tuple[Any, str] | None:
    slug, original = parse_qualified_name(tool_name)
    if slug:
        for server in servers:
            if server_slug(getattr(server, "name", "")) == slug:
                names = [str(n) for n in (getattr(server, "tool_names", None) or [])]
                schemas = ((getattr(server, "connection_config", None) or {}).get("tool_schemas") or [])
                schema_names = [str(s.get("name")) for s in schemas if isinstance(s, dict) and s.get("name")]
                if original in names or original in schema_names or not names:
                    return server, original
        return None

    matches: list[tuple[Any, str]] = []
    for server in servers:
        names = [str(n) for n in (getattr(server, "tool_names", None) or [])]
        schemas = ((getattr(server, "connection_config", None) or {}).get("tool_schemas") or [])
        schema_names = [str(s.get("name")) for s in schemas if isinstance(s, dict) and s.get("name")]
        if original in names or original in schema_names:
            matches.append((server, original))
    if len(matches) == 1:
        return matches[0]
    return None


def build_multiplex_catalog(servers: list[Any], *, auto_hide_destructive: bool = False) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for server in servers:
        slug = server_slug(getattr(server, "name", ""))
        tools = catalog_from_servers([server], auto_hide_destructive=auto_hide_destructive)
        for tool in tools:
            catalog.append(
                {
                    "name": qualify_tool_name(slug, tool["name"]),
                    "description": tool.get("description") or f"{getattr(server, 'name', slug)} / {tool['name']}",
                    "inputSchema": tool.get("inputSchema") or {"type": "object"},
                }
            )
    return catalog


def jsonrpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_jsonrpc(
    payload: dict[str, Any],
    servers: list[Any],
    *,
    auto_hide_destructive: bool = False,
) -> dict[str, Any]:
    request_id = payload.get("id")
    method = str(payload.get("method") or "")
    if method in {"initialize", "notifications/initialized"}:
        return jsonrpc_result(
            request_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": MULTIPLEX_SERVER_NAME, "version": "1.0"},
            },
        )
    if method == "ping":
        return jsonrpc_result(request_id, {})
    if method == "tools/list":
        return jsonrpc_result(request_id, {"tools": build_multiplex_catalog(servers, auto_hide_destructive=auto_hide_destructive)})
    if method == "tools/call":
        return jsonrpc_error(request_id, -32603, "tools/call must be handled asynchronously")
    return jsonrpc_error(request_id, -32601, f"Method not found: {method}")


def multiplex_public_path() -> str:
    return "/v1/mcp"


BeforeInvokeHook = Callable[[Any, str, dict[str, Any]], Awaitable[tuple[bool, str]]]
AfterInvokeHook = Callable[[Any, str, str], Awaitable[tuple[bool, str, str]]]


async def handle_tools_call(
    payload: dict[str, Any],
    servers: list[Any],
    access_token_for=None,
    *,
    auto_hide_destructive: bool = False,
    url_filter_policy: dict[str, Any] | None = None,
    vendor_api_key: str | None = None,
    before_invoke: BeforeInvokeHook | None = None,
    after_invoke: AfterInvokeHook | None = None,
) -> dict[str, Any]:
    from app.services.mcp_client_service import invoke_mcp_tool
    from app.services.mcp_tool_risk_service import tool_is_visible
    from app.services.mcp_url_filter_service import evaluate_tool_access

    request_id = payload.get("id")
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    tool_name = str(params.get("name") or "").strip()
    arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
    if not tool_name:
        return jsonrpc_error(request_id, -32602, "Tool name is required")
    target = resolve_tool_target(servers, tool_name)
    if target is None:
        return jsonrpc_error(request_id, -32602, f"Unknown tool: {tool_name}")
    server, original = target
    if not tool_is_visible(server, original, auto_hide_destructive=auto_hide_destructive):
        return jsonrpc_error(request_id, -32001, f"Tool is hidden by risk policy: {original}")
    if before_invoke is not None:
        allowed, reason = await before_invoke(server, original, arguments)
        if not allowed:
            return jsonrpc_error(request_id, -32003, reason or "Tool invocation blocked by policy")
    allowed, reason = await evaluate_tool_access(
        original,
        arguments,
        url_filter_policy or {},
        vendor_api_key=vendor_api_key,
    )
    if not allowed:
        return jsonrpc_error(request_id, -32002, reason or "URL blocked by policy")
    token = await access_token_for(server) if access_token_for else None
    result = await invoke_mcp_tool(server, original, arguments, access_token=token)
    if not result.ok:
        return jsonrpc_error(request_id, -32000, result.message)
    result_text = str(result.result)
    if after_invoke is not None:
        egress_ok, egress_reason, result_text = await after_invoke(server, original, result_text)
        if not egress_ok:
            return jsonrpc_error(request_id, -32004, egress_reason or "Tool response blocked by policy")
    return jsonrpc_result(
        request_id,
        {
            "content": [{"type": "text", "text": result_text}],
            "isError": False,
            "structuredContent": result.result if result_text == str(result.result) else result_text,
            "_pysetu": {"server": getattr(server, "name", ""), "tool": original, "latency_ms": result.latency_ms},
        },
    )


async def dispatch_mcp_request(
    payload: dict[str, Any],
    servers: list[Any],
    access_token_for=None,
    *,
    auto_hide_destructive: bool = False,
    url_filter_policy: dict[str, Any] | None = None,
    vendor_api_key: str | None = None,
    before_invoke: BeforeInvokeHook | None = None,
    after_invoke: AfterInvokeHook | None = None,
    catalog_filter: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    method = str(payload.get("method") or "")
    if method == "tools/call":
        return await handle_tools_call(
            payload,
            servers,
            access_token_for=access_token_for,
            auto_hide_destructive=auto_hide_destructive,
            url_filter_policy=url_filter_policy,
            vendor_api_key=vendor_api_key,
            before_invoke=before_invoke,
            after_invoke=after_invoke,
        )
    if method == "tools/list" and catalog_filter is not None:
        request_id = payload.get("id")
        catalog = build_multiplex_catalog(servers, auto_hide_destructive=auto_hide_destructive)
        return jsonrpc_result(request_id, {"tools": catalog_filter(catalog)})
    return handle_jsonrpc(payload, servers, auto_hide_destructive=auto_hide_destructive)
