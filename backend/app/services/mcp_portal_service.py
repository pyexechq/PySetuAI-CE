"""Self-service MCP portal — end-user browse and personal connect (BL-070)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import MCPServer, UserMcpConnection
from app.models.tenant import Tenant, User
from app.services.mcp_catalog_service import get_catalog_entry
from app.services.mcp_oauth_broker_service import load_oauth_state, resolve_access_token_local


def portal_visible(server: MCPServer) -> bool:
    config = server.connection_config or {}
    if config.get("portal_visible") is False:
        return False
    return True


def set_portal_visible(server: MCPServer, visible: bool) -> None:
    config = dict(server.connection_config or {})
    config["portal_visible"] = bool(visible)
    server.connection_config = config


def catalog_slug_for_server(server: MCPServer) -> str | None:
    config = server.connection_config or {}
    slug = config.get("catalog_slug")
    if isinstance(slug, str) and slug.strip():
        return slug.strip().lower()
    return None


def server_auth_required(server: MCPServer) -> bool:
    slug = catalog_slug_for_server(server)
    if slug:
        entry = get_catalog_entry(slug)
        if entry is not None:
            return bool(entry.get("auth_required"))
    config = server.connection_config or {}
    return bool(config.get("auth_required"))


def connection_status(
    server: MCPServer,
    *,
    user_connected: bool,
    tenant_token_available: bool,
) -> str:
    if not server_auth_required(server):
        return "ready"
    if user_connected or tenant_token_available:
        return "connected"
    return "needs_auth"


async def load_user_connection(db: AsyncSession, user_id, server_id) -> UserMcpConnection | None:
    result = await db.execute(
        select(UserMcpConnection).where(
            UserMcpConnection.user_id == user_id,
            UserMcpConnection.server_id == server_id,
        )
    )
    return result.scalar_one_or_none()


async def user_has_token(db: AsyncSession, tenant_id, user_id, server_id) -> bool:
    from app.services.secrets_service import get_user_mcp_secret

    row = await load_user_connection(db, user_id, server_id)
    if row is None:
        return False
    token = await get_user_mcp_secret(tenant_id, user_id, server_id, row.access_token)
    return bool((token or "").strip())


async def tenant_has_token(db: AsyncSession, server: MCPServer) -> bool:
    state = await load_oauth_state(db, server.tenant_id, server.id)
    if state is None or not state.enabled:
        return False
    return bool(resolve_access_token_local(state))


async def list_portal_entries(
    db: AsyncSession,
    user: User,
    tenant: Tenant,
    servers: list[MCPServer],
) -> list[dict[str, Any]]:
    if not tenant.mcp_portal_enabled:
        return []

    entries: list[dict[str, Any]] = []
    for server in servers:
        if not portal_visible(server):
            continue
        user_connected = await user_has_token(db, tenant.id, user.id, server.id)
        tenant_connected = await tenant_has_token(db, server)
        status = connection_status(
            server,
            user_connected=user_connected,
            tenant_token_available=tenant_connected,
        )
        slug = catalog_slug_for_server(server)
        vendor = ""
        description = ""
        if slug:
            catalog = get_catalog_entry(slug)
            if catalog:
                vendor = str(catalog.get("vendor") or "")
                description = str(catalog.get("description") or "")
        entries.append(
            {
                "server_id": str(server.id),
                "name": server.name,
                "category": server.category,
                "status": server.status,
                "tool_count": server.tools_count or 0,
                "tool_names": list(server.tool_names or [])[:8],
                "auth_required": server_auth_required(server),
                "connection_status": status,
                "catalog_slug": slug,
                "vendor": vendor,
                "description": description,
                "portal_visible": True,
            }
        )
    return entries


async def connect_user_token(
    db: AsyncSession,
    user: User,
    server: MCPServer,
    access_token: str,
) -> None:
    from app.services.secrets_service import set_user_mcp_secret

    token = (access_token or "").strip()
    if not token:
        raise ValueError("Access token is required")

    row = await load_user_connection(db, user.id, server.id)
    if row is None:
        row = UserMcpConnection(
            tenant_id=user.tenant_id,
            user_id=user.id,
            server_id=server.id,
        )
        db.add(row)
    row.connected_at = datetime.now(UTC)
    row.access_token = await set_user_mcp_secret(user.tenant_id, user.id, server.id, token)
    await db.commit()


async def disconnect_user(db: AsyncSession, user: User, server_id) -> bool:
    from app.services.secrets_service import set_user_mcp_secret

    row = await load_user_connection(db, user.id, server_id)
    if row is None:
        return False
    await set_user_mcp_secret(user.tenant_id, user.id, server_id, None)
    await db.execute(
        delete(UserMcpConnection).where(
            UserMcpConnection.user_id == user.id,
            UserMcpConnection.server_id == server_id,
        )
    )
    await db.commit()
    return True


async def resolve_user_mcp_access_token(db: AsyncSession, user_id, server: MCPServer) -> str | None:
    from app.services.secrets_service import get_user_mcp_secret

    row = await load_user_connection(db, user_id, server.id)
    if row is None:
        return None
    token = await get_user_mcp_secret(server.tenant_id, user_id, server.id, row.access_token)
    return (token or "").strip() or None


async def resolve_effective_mcp_access_token(
    db: AsyncSession,
    server: MCPServer,
    *,
    user_id=None,
) -> str | None:
    from app.services.mcp_oauth_broker_service import resolve_mcp_access_token

    if user_id is not None:
        user_token = await resolve_user_mcp_access_token(db, user_id, server)
        if user_token:
            return user_token
    return await resolve_mcp_access_token(db, server)
