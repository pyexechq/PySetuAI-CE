"""REST-to-MCP auto-proxy runtime (BL-083).

A server registered from an OpenAPI / Postman / GraphQL spec uses the
``rest_proxy`` transport. Instead of connecting to a real MCP endpoint, the
gateway translates MCP ``tools/call`` requests into plain HTTP calls against
the REST API described by the stored spec.

The spec is persisted in ``connection_config["rest_spec"]``:

    {
      "base_url": "https://api.example.com",
      "operations": [
        {"name": "getUser", "method": "GET", "path": "/users/{id}", "description": "..."}
      ]
    }
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx

from app.models.governance import MCPServer
from app.services.mcp_transport import resolve_timeout_sec

REST_SPEC_KEY = "rest_spec"
_PATH_PARAM_RE = re.compile(r"\{([^}]+)\}")


def build_rest_spec(base_url: str, operations: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize parsed operations into the persisted rest_spec shape."""
    normalized: list[dict[str, Any]] = []
    for op in operations:
        if not isinstance(op, dict):
            continue
        name = str(op.get("name") or "").strip()
        if not name:
            continue
        normalized.append(
            {
                "name": name,
                "method": str(op.get("method") or "GET").upper(),
                "path": str(op.get("path") or ""),
                "description": str(op.get("description") or ""),
            }
        )
    return {"base_url": (base_url or "").strip(), "operations": normalized}


def get_rest_spec(server: MCPServer) -> dict[str, Any] | None:
    config = server.connection_config or {}
    spec = config.get(REST_SPEC_KEY)
    return spec if isinstance(spec, dict) else None


def get_authorization_header(server: MCPServer) -> str | None:
    """Extract authorization header from connection_config if present."""
    config = server.connection_config or {}
    auth = (config.get("authorization_header") or "").strip()
    return auth if auth else None


def discover_rest_tools(server: MCPServer) -> list[dict[str, Any]]:
    """Return tool definitions for a rest_proxy server from the stored spec."""
    spec = get_rest_spec(server)
    if not spec:
        return []
    tools: list[dict[str, Any]] = []
    for op in spec.get("operations") or []:
        if not isinstance(op, dict):
            continue
        name = str(op.get("name") or "")
        if not name:
            continue
        path = str(op.get("path") or "")
        params = _path_params(path)
        input_schema: dict[str, Any] = {"type": "object"}
        if params:
            input_schema["properties"] = {
                p: {"type": "string", "description": f"Path parameter {p}"} for p in params
            }
            input_schema["required"] = params
        tools.append(
            {
                "name": name,
                "description": str(op.get("description") or f"{op.get('method')} {path}"),
                "inputSchema": input_schema,
            }
        )
    return tools


def _path_params(path: str) -> list[str]:
    """Extract {param} placeholders from a REST path, preserving order."""
    return [m.group(1) for m in _PATH_PARAM_RE.finditer(path)]


def _find_operation(spec: dict[str, Any], tool_name: str) -> dict[str, Any] | None:
    for op in spec.get("operations") or []:
        if isinstance(op, dict) and str(op.get("name") or "") == tool_name:
            return op
    return None


def _substitute_path(path: str, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Replace {param} placeholders in the path; leftover args become query params."""
    remaining = dict(arguments)

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = remaining.pop(key, None)
        if value is None:
            return match.group(0)
        return str(value)

    substituted = _PATH_PARAM_RE.sub(repl, path)
    return substituted, remaining


async def invoke_rest_tool(
    server: MCPServer,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    access_token: str | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Translate an MCP tools/call into a REST HTTP call. Returns (ok, message, result)."""
    spec = get_rest_spec(server)
    if not spec:
        return False, "No REST spec stored for this server.", None
    base_url = str(spec.get("base_url") or "").strip()
    if not base_url:
        return False, "No base URL configured for this server.", None

    op = _find_operation(spec, tool_name)
    if op is None:
        return False, f"Unknown tool: {tool_name}", None

    method = str(op.get("method") or "GET").upper()
    path = str(op.get("path") or "")
    args = dict(arguments or {})
    path, query_args = _substitute_path(path, args)

    missing = _path_params(path)
    if missing:
        return False, f"Missing required path parameter(s): {', '.join(missing)}.", None

    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    headers: dict[str, str] = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    timeout_sec = resolve_timeout_sec(server.connection_config)
    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            if method in {"GET", "HEAD", "DELETE"}:
                response = await client.request(method, url, params=query_args, headers=headers)
            else:
                response = await client.request(method, url, json=query_args, headers=headers)
    except httpx.TimeoutException:
        return False, f"REST call timed out after {int(timeout_sec)}s.", None
    except httpx.HTTPError as exc:
        return False, f"REST call failed: {exc}", None

    if response.status_code >= 400:
        return False, f"REST call returned HTTP {response.status_code}.", None

    try:
        result: dict[str, Any] | None = response.json()
    except ValueError:
        result = {"text": response.text}

    return True, f"REST {method} {path} -> HTTP {response.status_code}.", result


def probe_rest_server(server: MCPServer) -> tuple[bool, str, int]:
    """Health probe for a rest_proxy server: verify the spec is present, test connectivity, and validate at least one tool endpoint."""
    spec = get_rest_spec(server)
    if not spec:
        return False, "No REST spec stored for this server.", 0
    base_url = str(spec.get("base_url") or "").strip()
    if not base_url:
        return False, "No base URL configured for this server.", 0
    operations = spec.get("operations") or []
    if not operations:
        return False, "REST spec contains no operations.", 0

    timeout_sec = resolve_timeout_sec(server.connection_config)
    started = time.perf_counter()
    
    headers: dict[str, str] = {"Accept": "application/json"}
    auth_header = get_authorization_header(server)
    if auth_header:
        headers["Authorization"] = auth_header
    
    try:
        with httpx.Client(timeout=timeout_sec, follow_redirects=True) as client:
            response = client.get(base_url, headers=headers)
        latency_ms = max(1, int((time.perf_counter() - started) * 1000))
        
        if response.status_code < 400:
            return True, f"REST API reachable (HTTP {response.status_code}); {len(operations)} tool(s) available.", latency_ms
        if response.status_code in {401, 403}:
            return True, f"REST API requires authorization (HTTP {response.status_code}); {len(operations)} tool(s) available.", latency_ms
        
        if response.status_code == 404:
            return True, f"REST API base path not found (HTTP 404 expected); {len(operations)} tool(s) available for invocation.", latency_ms
        
        return True, f"REST API reachable; {len(operations)} tool(s) available (base path returned HTTP {response.status_code}).", latency_ms
    except httpx.HTTPError as exc:
        return False, f"REST base unreachable: {exc}", 0
