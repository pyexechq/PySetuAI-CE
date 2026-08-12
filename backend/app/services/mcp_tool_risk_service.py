"""MCP tool risk taxonomy — read / write / destructive + auto-hide (BL-068)."""

from __future__ import annotations

import re
from typing import Any

RISK_READ = "read"
RISK_WRITE = "write"
RISK_DESTRUCTIVE = "destructive"
ALLOWED_RISKS = {RISK_READ, RISK_WRITE, RISK_DESTRUCTIVE}

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_DESTRUCTIVE_TOKENS = {
    "delete",
    "destroy",
    "drop",
    "purge",
    "remove",
    "rm",
    "truncate",
    "unlink",
    "wipe",
    "kill",
    "revoke",
    "erase",
}
_WRITE_TOKENS = {
    "create",
    "update",
    "write",
    "post",
    "send",
    "put",
    "patch",
    "insert",
    "set",
    "add",
    "upload",
    "move",
    "rename",
    "append",
    "edit",
    "replace",
}
_READ_TOKENS = {
    "get",
    "list",
    "search",
    "read",
    "fetch",
    "find",
    "describe",
    "query",
    "lookup",
    "show",
    "view",
    "stat",
}


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower().replace("-", "_").replace("_", " ")))


def classify_tool_risk(name: str, description: str = "") -> str:
    tokens = _tokens(f"{name} {description}")
    if tokens & _DESTRUCTIVE_TOKENS:
        return RISK_DESTRUCTIVE
    if tokens & _WRITE_TOKENS:
        return RISK_WRITE
    if tokens & _READ_TOKENS:
        return RISK_READ
    return RISK_READ


def policies_from_config(connection_config: dict | None) -> dict[str, dict[str, Any]]:
    config = connection_config if isinstance(connection_config, dict) else {}
    raw = config.get("tool_risk") or {}
    if not isinstance(raw, dict):
        return {}
    policies: dict[str, dict[str, Any]] = {}
    for name, value in raw.items():
        key = str(name).strip()
        if not key:
            continue
        if isinstance(value, dict):
            risk = str(value.get("risk") or "").strip().lower()
            policies[key] = {
                "risk": risk if risk in ALLOWED_RISKS else None,
                "hidden": bool(value.get("hidden")),
            }
        elif isinstance(value, str) and value.strip().lower() in ALLOWED_RISKS:
            policies[key] = {"risk": value.strip().lower(), "hidden": False}
    return policies


def resolve_tool_policy(name: str, description: str, policies: dict[str, dict[str, Any]] | None) -> dict[str, Any]:
    override = (policies or {}).get(name) or {}
    risk = override.get("risk") if override.get("risk") in ALLOWED_RISKS else classify_tool_risk(name, description)
    return {"risk": risk, "hidden": bool(override.get("hidden"))}


def is_tool_hidden(policy: dict[str, Any], *, auto_hide_destructive: bool = False) -> bool:
    if bool(policy.get("hidden")):
        return True
    return auto_hide_destructive and policy.get("risk") == RISK_DESTRUCTIVE


def annotate_tools(
    tools: list[dict[str, Any]],
    policies: dict[str, dict[str, Any]] | None = None,
    *,
    auto_hide_destructive: bool = False,
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or "").strip()
        if not name:
            continue
        description = str(tool.get("description") or "")
        policy = resolve_tool_policy(name, description, policies)
        hidden = bool(policy["hidden"])
        auto_hidden = (not hidden) and auto_hide_destructive and policy["risk"] == RISK_DESTRUCTIVE
        item = dict(tool)
        item["name"] = name
        item["description"] = description
        item["risk"] = policy["risk"]
        item["hidden"] = hidden
        item["auto_hidden"] = auto_hidden
        item["visible"] = not (hidden or auto_hidden)
        annotated.append(item)
    return annotated


def visible_tools(
    tools: list[dict[str, Any]],
    policies: dict[str, dict[str, Any]] | None = None,
    auto_hide_destructive: bool = False,
) -> list[dict[str, Any]]:
    return [tool for tool in annotate_tools(tools, policies, auto_hide_destructive=auto_hide_destructive) if tool["visible"]]


def merge_tool_policies(
    existing: dict[str, dict[str, Any]] | None,
    updates: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    merged = {str(k): dict(v) for k, v in (existing or {}).items()}
    for item in updates:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        current = dict(merged.get(name) or {"risk": None, "hidden": False})
        if "risk" in item and item["risk"] is not None:
            risk = str(item["risk"]).strip().lower()
            if risk not in ALLOWED_RISKS:
                raise ValueError(f"risk must be one of: {', '.join(sorted(ALLOWED_RISKS))}")
            current["risk"] = risk
        if "hidden" in item and item["hidden"] is not None:
            current["hidden"] = bool(item["hidden"])
        merged[name] = current
    return merged


def apply_policies_to_config(connection_config: dict | None, policies: dict[str, dict[str, Any]]) -> dict:
    config = dict(connection_config or {})
    stored: dict[str, dict[str, Any]] = {}
    for name, policy in policies.items():
        entry: dict[str, Any] = {"hidden": bool(policy.get("hidden"))}
        if policy.get("risk") in ALLOWED_RISKS:
            entry["risk"] = policy["risk"]
        stored[name] = entry
    config["tool_risk"] = stored
    return config


def _tool_description(server: Any, tool_name: str) -> str:
    config = getattr(server, "connection_config", None) or {}
    schemas = config.get("tool_schemas") if isinstance(config, dict) else None
    if isinstance(schemas, list):
        for schema in schemas:
            if isinstance(schema, dict) and str(schema.get("name") or "") == tool_name:
                return str(schema.get("description") or "")
    return ""


def tool_is_visible(server: Any, tool_name: str, *, auto_hide_destructive: bool = False) -> bool:
    policy = resolve_tool_policy(
        tool_name,
        _tool_description(server, tool_name),
        policies_from_config(getattr(server, "connection_config", None)),
    )
    return not is_tool_hidden(policy, auto_hide_destructive=auto_hide_destructive)
