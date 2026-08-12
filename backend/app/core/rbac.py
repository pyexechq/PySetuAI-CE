"""Centralized role-based access control."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.tenant import User

# Permission constants (aligned with docs/security/README.md)
MANAGE_TENANTS = "manage_tenants"
MANAGE_USERS = "manage_users"
MANAGE_POLICIES = "manage_policies"
VIEW_AUDIT_LOGS = "view_audit_logs"
INGEST_AUDIT_LOGS = "ingest_audit_logs"
MANAGE_MCP = "manage_mcp"
USE_MCP = "use_mcp"
USE_STUDIO = "use_studio"
VIEW_COMPLIANCE = "view_compliance"
MANAGE_LLM_PROVIDERS = "manage_llm_providers"

ALL_PERMISSIONS: tuple[str, ...] = (
    MANAGE_TENANTS,
    MANAGE_USERS,
    MANAGE_POLICIES,
    VIEW_AUDIT_LOGS,
    INGEST_AUDIT_LOGS,
    MANAGE_MCP,
    USE_MCP,
    USE_STUDIO,
    VIEW_COMPLIANCE,
    MANAGE_LLM_PROVIDERS,
)

VALID_ROLES: tuple[str, ...] = (
    "platform_admin",
    "tenant_admin",
    "security_admin",
    "compliance_officer",
    "auditor",
    "developer",
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "platform_admin": frozenset(ALL_PERMISSIONS),
    "tenant_admin": frozenset(p for p in ALL_PERMISSIONS if p != MANAGE_TENANTS),
    "security_admin": frozenset(
        {
            MANAGE_POLICIES,
            VIEW_AUDIT_LOGS,
            INGEST_AUDIT_LOGS,
            MANAGE_MCP,
            USE_MCP,
            USE_STUDIO,
            MANAGE_LLM_PROVIDERS,
        }
    ),
    "compliance_officer": frozenset({VIEW_AUDIT_LOGS, VIEW_COMPLIANCE}),
    "auditor": frozenset({VIEW_AUDIT_LOGS, VIEW_COMPLIANCE}),
    "developer": frozenset({USE_STUDIO, USE_MCP}),
}

PERMISSION_LABELS: dict[str, str] = {
    MANAGE_TENANTS: "Manage tenants",
    MANAGE_USERS: "Manage users",
    MANAGE_POLICIES: "Manage policies",
    VIEW_AUDIT_LOGS: "View audit logs",
    INGEST_AUDIT_LOGS: "Ingest audit logs",
    MANAGE_MCP: "Manage MCP servers",
    USE_MCP: "Use MCP portal",
    USE_STUDIO: "Use Governance Sandbox",
    VIEW_COMPLIANCE: "View compliance",
    MANAGE_LLM_PROVIDERS: "Manage LLM providers",
}


def role_has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def permissions_for_role(role: str) -> list[str]:
    return sorted(ROLE_PERMISSIONS.get(role, frozenset()))


def require_permission(permission: str) -> Callable[..., User]:
    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not role_has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}",
            )
        return current_user

    return _check


def require_any_permission(*permissions: str) -> Callable[..., User]:
    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not any(role_has_permission(current_user.role, p) for p in permissions):
            names = ", ".join(permissions)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions required: {names}",
            )
        return current_user

    return _check


def require_roles(*roles: str) -> Callable[..., User]:
    allowed = set(roles)

    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role privileges",
            )
        return current_user

    return _check
