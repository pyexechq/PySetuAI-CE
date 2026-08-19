"""MCP access control — bundle scope, deny lists, actor role (BL-101, BL-099)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import McpToolDenyRule, MCPToolPolicy, PolicyBundle
from app.services.gateway_context import GatewayContext
from app.services.mcp_security_service import is_tool_denied
from app.services.mcp_tool_policy_service import resolve_tool_action

CLIENT_KEY_ROLE = "client_key"


def resolve_actor_role(ctx: GatewayContext) -> str:
    if ctx.user and getattr(ctx.user, "role", None):
        return str(ctx.user.role)
    return CLIENT_KEY_ROLE


def parse_mcp_scope(bundle: PolicyBundle | None) -> dict[str, Any]:
    if bundle is None:
        return {"mode": "all", "entries": []}
    scope = getattr(bundle, "mcp_scope", None)
    if not scope or not isinstance(scope, dict):
        return {"mode": "all", "entries": []}
    mode = str(scope.get("mode") or "all").strip().lower()
    entries = scope.get("entries") if isinstance(scope.get("entries"), list) else []
    return {"mode": mode, "entries": entries}


def filter_servers_for_bundle(servers: list[Any], bundle: PolicyBundle | None) -> list[Any]:
    scope = parse_mcp_scope(bundle)
    if scope["mode"] != "allowlist":
        return servers
    allowed_ids = {
        str(entry.get("server_id"))
        for entry in scope["entries"]
        if isinstance(entry, dict) and entry.get("server_id")
    }
    return [server for server in servers if str(getattr(server, "id", "")) in allowed_ids]


def _entry_for_server(scope: dict[str, Any], server_id: uuid.UUID) -> dict[str, Any] | None:
    for entry in scope["entries"]:
        if isinstance(entry, dict) and str(entry.get("server_id")) == str(server_id):
            return entry
    return None


def is_tool_in_bundle_scope(bundle: PolicyBundle | None, server_id: uuid.UUID, tool_name: str) -> tuple[bool, str]:
    scope = parse_mcp_scope(bundle)
    if scope["mode"] != "allowlist":
        return True, ""
    entry = _entry_for_server(scope, server_id)
    if entry is None:
        return False, "MCP server not allowed by policy bundle"
    tool_names = entry.get("tool_names")
    if not tool_names:
        return True, ""
    allowed = {str(name).casefold() for name in tool_names}
    if tool_name.casefold() in allowed:
        return True, ""
    return False, f"Tool '{tool_name}' not allowed by policy bundle"


def check_tool_access(
    bundle: PolicyBundle | None,
    deny_rules: list[McpToolDenyRule],
    actor_role: str,
    server: Any,
    tool_name: str,
) -> tuple[bool, str]:
    server_id = getattr(server, "id", None)
    if server_id is None:
        return False, "Invalid MCP server"
    allowed, reason = is_tool_in_bundle_scope(bundle, server_id, tool_name)
    if not allowed:
        return False, reason
    if is_tool_denied(deny_rules, actor_role, server_id, tool_name):
        return False, f"Tool '{tool_name}' denied for role '{actor_role}'"
    return True, ""


async def check_tool_policy_action(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    bundle: PolicyBundle | None,
    deny_rules: list[McpToolDenyRule],
    actor_role: str,
    server: Any,
    tool_name: str,
) -> tuple[str, str, MCPToolPolicy | None]:
    """Compose deny-list + bundle scope with per-tool governance policy.

    Returns ``(action, reason, policy)`` where action is one of
    ``allow`` | ``approval`` | ``block``. The deny-list and bundle scope act as
    the hard ``block`` baseline; the per-tool policy adds ``approval`` on top.
    """
    allowed, reason = check_tool_access(bundle, deny_rules, actor_role, server, tool_name)
    if not allowed:
        return "block", reason, None
    server_id = getattr(server, "id", None)
    if server_id is None:
        return "block", "Invalid MCP server", None
    action, policy = await resolve_tool_action(db, tenant_id, server_id, tool_name)
    if action == "block":
        return "block", f"Tool '{tool_name}' blocked by governance policy", policy
    if action == "approval":
        return "approval", f"Tool '{tool_name}' requires approval", policy
    return "allow", "", policy


def filter_multiplex_catalog(
    catalog: list[dict[str, Any]],
    servers: list[Any],
    bundle: PolicyBundle | None,
    deny_rules: list[McpToolDenyRule],
    actor_role: str,
    *,
    slug_for_server: Any,
    parse_qualified_name: Any,
) -> list[dict[str, Any]]:
    """Filter multiplex tool list by bundle scope and deny rules."""
    server_by_slug: dict[str, Any] = {}
    for server in servers:
        server_by_slug[slug_for_server(getattr(server, "name", ""))] = server

    filtered: list[dict[str, Any]] = []
    for tool in catalog:
        qualified = str(tool.get("name") or "")
        slug, original = parse_qualified_name(qualified)
        if not slug:
            continue
        server = server_by_slug.get(slug)
        if server is None:
            continue
        allowed, _ = check_tool_access(bundle, deny_rules, actor_role, server, original)
        if allowed:
            filtered.append(tool)
    return filtered
