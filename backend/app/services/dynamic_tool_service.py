"""Dynamic MCP tool ranking — send only relevant tools to the model (BL-064)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.services.token_saving_service import estimate_tokens

_TOKEN_RE = re.compile(r"[a-z0-9_]{3,}")
DEFAULT_MAX_TOOLS = 8


@dataclass
class DynamicToolResult:
    selected: list[dict[str, Any]]
    enabled: bool
    catalog_count: int
    selected_count: int
    original_tokens: int
    compressed_tokens: int
    tokens_saved: int
    savings_pct: float
    selected_names: list[str] = field(default_factory=list)


def _normalize_tool(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("name") or raw.get("function", {}).get("name") or "")
    if raw.get("type") == "function" and isinstance(raw.get("function"), dict):
        fn = raw["function"]
        return {
            "name": str(fn.get("name") or name),
            "description": str(fn.get("description") or ""),
            "inputSchema": fn.get("parameters") or {"type": "object"},
        }
    return {
        "name": name,
        "description": str(raw.get("description") or ""),
        "inputSchema": raw.get("inputSchema") or raw.get("input_schema") or {"type": "object"},
    }


def to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    openai_tools: list[dict[str, Any]] = []
    for tool in tools:
        normalized = _normalize_tool(tool)
        if not normalized["name"]:
            continue
        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": normalized["name"],
                    "description": normalized["description"],
                    "parameters": normalized["inputSchema"] or {"type": "object"},
                },
            }
        )
    return openai_tools


def tool_token_estimate(tools: list[dict[str, Any]]) -> int:
    if not tools:
        return 0
    payload = json.dumps(to_openai_tools(tools), separators=(",", ":"))
    return estimate_tokens(payload)


def tools_from_server(server: Any) -> list[dict[str, Any]]:
    config = getattr(server, "connection_config", None) or {}
    schemas = config.get("tool_schemas") if isinstance(config, dict) else None
    tools: list[dict[str, Any]] = []
    seen: set[str] = set()
    if isinstance(schemas, list) and schemas:
        for schema in schemas:
            if not isinstance(schema, dict):
                continue
            normalized = _normalize_tool(schema)
            if normalized["name"] and normalized["name"] not in seen:
                seen.add(normalized["name"])
                tools.append(normalized)
        return tools
    for name in getattr(server, "tool_names", None) or []:
        tool_name = str(name)
        if tool_name and tool_name not in seen:
            seen.add(tool_name)
            tools.append({"name": tool_name, "description": "", "inputSchema": {"type": "object"}})
    return tools


def catalog_from_servers(
    servers: list[Any],
    *,
    include_hidden: bool = False,
    auto_hide_destructive: bool = False,
) -> list[dict[str, Any]]:
    from app.services.mcp_tool_risk_service import policies_from_config, annotate_tools, visible_tools

    catalog: list[dict[str, Any]] = []
    seen: set[str] = set()
    for server in servers:
        raw = tools_from_server(server)
        policies = policies_from_config(getattr(server, "connection_config", None))
        if include_hidden:
            selected = annotate_tools(raw, policies, auto_hide_destructive=auto_hide_destructive)
        else:
            selected = visible_tools(raw, policies, auto_hide_destructive=auto_hide_destructive)
        for tool in selected:
            name = tool["name"]
            if name and name not in seen:
                seen.add(name)
                catalog.append(tool)
    return catalog


def _query_tokens(query: str) -> set[str]:
    return set(_TOKEN_RE.findall(query.lower().replace("-", "_")))


def _score_tool(query_tokens: set[str], tool: dict[str, Any]) -> int:
    blob = f"{tool.get('name', '')} {tool.get('description', '')}".lower().replace("-", "_")
    tool_tokens = set(_TOKEN_RE.findall(blob))
    if not query_tokens or not tool_tokens:
        return 0
    return len(query_tokens & tool_tokens)


def resolve_dynamic_tool_config(
    *,
    tenant_enabled: bool,
    tenant_max_tools: int,
    request_metadata: dict | None,
) -> tuple[bool, int]:
    enabled = tenant_enabled
    max_tools = tenant_max_tools or DEFAULT_MAX_TOOLS
    if request_metadata:
        if "dynamic_tool_calling" in request_metadata:
            enabled = bool(request_metadata["dynamic_tool_calling"])
        if request_metadata.get("dynamic_tool_max"):
            try:
                max_tools = int(request_metadata["dynamic_tool_max"])
            except (TypeError, ValueError):
                pass
    max_tools = max(1, min(max_tools, 64))
    return enabled, max_tools


def rank_and_filter_tools(
    query: str,
    tools: list[dict[str, Any]],
    *,
    max_tools: int = DEFAULT_MAX_TOOLS,
    enabled: bool = True,
) -> DynamicToolResult:
    normalized = [_normalize_tool(t) for t in tools if isinstance(t, dict)]
    normalized = [t for t in normalized if t["name"]]
    catalog_count = len(normalized)
    original_tokens = tool_token_estimate(normalized)

    if not enabled:
        return DynamicToolResult(
            selected=normalized,
            enabled=False,
            catalog_count=catalog_count,
            selected_count=catalog_count,
            original_tokens=original_tokens,
            compressed_tokens=original_tokens,
            tokens_saved=0,
            savings_pct=0.0,
            selected_names=[t["name"] for t in normalized],
        )

    cap = max(1, min(max_tools, 64))
    query_tokens = _query_tokens(query)
    ranked = sorted(
        normalized,
        key=lambda tool: (-_score_tool(query_tokens, tool), tool["name"]),
    )
    selected = ranked[:cap]
    compressed_tokens = tool_token_estimate(selected)
    tokens_saved = max(0, original_tokens - compressed_tokens)
    savings_pct = round((tokens_saved / original_tokens) * 100, 1) if original_tokens else 0.0
    return DynamicToolResult(
        selected=selected,
        enabled=True,
        catalog_count=catalog_count,
        selected_count=len(selected),
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        tokens_saved=tokens_saved,
        savings_pct=savings_pct,
        selected_names=[t["name"] for t in selected],
    )


def apply_dynamic_tools_for_request(
    servers: list[Any],
    query: str,
    request_tools: list[dict[str, Any]] | None,
    *,
    enabled: bool,
    max_tools: int,
    auto_hide_destructive: bool = False,
) -> DynamicToolResult:
    catalog = catalog_from_servers(servers, auto_hide_destructive=auto_hide_destructive)
    if request_tools:
        incoming = [_normalize_tool(t) for t in request_tools if isinstance(t, dict)]
        seen = {t["name"] for t in catalog}
        for tool in incoming:
            if tool["name"] and tool["name"] not in seen:
                catalog.append(tool)
                seen.add(tool["name"])
    return rank_and_filter_tools(query, catalog, max_tools=max_tools, enabled=enabled)
