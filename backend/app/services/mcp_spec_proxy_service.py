"""BL-083 — REST-to-MCP auto-proxy spec parsing (server-side).

Parses OpenAPI 3.x / Swagger 2.0, Postman Collection v2.x, and GraphQL SDL
into MCP tool definitions. Tool naming mirrors the frontend wizard
(`RestToMcpWizardModal`) so this endpoint is a drop-in for the client-side
parsers when a caller prefers server-side conversion.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.services.http_client_pool import get_http_client

PROTOCOLS = {"openapi_url", "openapi_json", "postman", "graphql"}
HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head")

_GRAPHQL_BLOCK_RE = re.compile(r"\btype\s+(Mutation|Query)\s*\{([^}]+)\}", re.IGNORECASE)
_GRAPHQL_FIELD_RE = re.compile(r"(\w+)\s*(?:\([^)]*\))?\s*:")


def to_tool_name(raw: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    return name[:64] or "unnamed_tool"


def _tool(
    name: str,
    description: str,
    method: str = "",
    path: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    tool: dict[str, Any] = {"name": to_tool_name(name), "description": description}
    if method:
        tool["method"] = method
    if path:
        tool["path"] = path
    if tags:
        tool["tags"] = tags
    return tool


def parse_openapi_spec(spec: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    tools: list[dict[str, Any]] = []
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return tools, _openapi_base_url(spec)

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in HTTP_METHODS:
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue
            operation_id = str(op.get("operationId") or "")
            summary = str(op.get("summary") or "")
            description = str(op.get("description") or summary)
            tags = op.get("tags") if isinstance(op.get("tags"), list) else []
            raw_name = operation_id or f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
            tools.append(
                _tool(
                    raw_name,
                    description or f"{method.upper()} {path}",
                    method=method.upper(),
                    path=str(path),
                    tags=[str(tag) for tag in tags],
                )
            )
    return tools, _openapi_base_url(spec)


def _openapi_base_url(spec: dict[str, Any]) -> str:
    servers = spec.get("servers")
    if isinstance(servers, list) and servers and isinstance(servers[0], dict):
        return str(servers[0].get("url") or "")
    if spec.get("host"):
        schemes = spec.get("schemes")
        scheme = "https" if isinstance(schemes, list) and "https" in schemes else "http"
        return f"{scheme}://{spec['host']}{spec.get('basePath') or ''}"
    return ""


def parse_postman_spec(collection: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    tools: list[dict[str, Any]] = []

    def traverse(items: Any) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("item"), list):
                traverse(item["item"])
                continue
            req = item.get("request")
            if not isinstance(req, dict):
                continue
            name = str(item.get("name") or "")
            method = str(req.get("method") or "GET")
            url = req.get("url")
            raw_path = ""
            if isinstance(url, str):
                raw_path = url
            elif isinstance(url, dict):
                path_parts = url.get("path")
                if isinstance(path_parts, list):
                    raw_path = "/".join(str(part) for part in path_parts)
            tools.append(
                _tool(
                    name or raw_path,
                    f"{method.upper()} {raw_path}" if raw_path else name,
                    method=method.upper(),
                    path=raw_path,
                )
            )

    traverse(collection.get("item"))
    info = collection.get("info")
    server_name = str(info.get("name") or "") if isinstance(info, dict) else ""
    return tools, server_name


def parse_graphql_sdl(sdl: str) -> tuple[list[dict[str, Any]], str]:
    tools: list[dict[str, Any]] = []
    for block in _GRAPHQL_BLOCK_RE.finditer(sdl):
        kind = block.group(1).lower()
        body = block.group(2)
        for field in _GRAPHQL_FIELD_RE.finditer(body):
            field_name = field.group(1)
            if field_name == "__typename":
                continue
            method = "MUTATION" if kind == "mutation" else "QUERY"
            tools.append(_tool(field_name, f"GraphQL {kind}: {field_name}", method, field_name, [kind]))
    return tools, ""


def _parse_json(text: str | None, label: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise ValueError(f"{label} text is required")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {label} JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    return parsed


async def parse_spec(
    protocol: str,
    spec_url: str | None = None,
    spec_text: str | None = None,
) -> dict[str, Any]:
    protocol = (protocol or "").strip().lower()
    if protocol not in PROTOCOLS:
        raise ValueError("protocol must be one of: openapi_url, openapi_json, postman, graphql")

    if protocol == "openapi_url":
        if not spec_url or not spec_url.strip():
            raise ValueError("spec_url is required for openapi_url")
        client = await get_http_client()
        try:
            res = await client.get(spec_url.strip(), timeout=30.0)
            res.raise_for_status()
            spec = res.json()
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"Spec URL fetch failed: HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise ValueError(f"Spec URL fetch failed: {exc}") from exc
        except ValueError as exc:
            raise ValueError("Spec URL did not return valid JSON") from exc
        tools, endpoint = parse_openapi_spec(spec)
    elif protocol == "openapi_json":
        tools, endpoint = parse_openapi_spec(_parse_json(spec_text, "OpenAPI spec"))
    elif protocol == "postman":
        tools, endpoint = parse_postman_spec(_parse_json(spec_text, "Postman collection"))
    else:  # graphql
        if not spec_text or not spec_text.strip():
            raise ValueError("spec_text is required for graphql")
        tools, endpoint = parse_graphql_sdl(spec_text)

    if not tools:
        raise ValueError("No operations found. Check the spec format and try again.")
    return {"protocol": protocol, "tools": tools, "endpoint_url": endpoint}
