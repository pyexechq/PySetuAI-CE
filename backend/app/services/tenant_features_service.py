"""Tenant module feature flags — platform entitlement + tenant preferences."""

from __future__ import annotations

from typing import Any

from app.models.tenant import Tenant

FEATURE_DEFINITIONS: dict[str, dict[str, str]] = {
    "qa_dashboard": {
        "label": "QA Dashboard",
        "description": "Release testing cycles, automated pytest runs, and defect tracking.",
        "route": "/qa-dashboard",
    },
    "compatibility_center": {
        "label": "Compatibility Center",
        "description": "Universal AI Gateway mappings, translation policies, and stats.",
        "route": "/compatibility-center",
    },
    "governance_sandbox": {
        "label": "Governance Sandbox",
        "description": "Prompt lab, policy dry-runs, translation simulator, and MCP testing.",
        "route": "/studio",
    },
    "reports": {
        "label": "Reports",
        "description": "Scheduled compliance and governance report exports.",
        "route": "/reports",
    },
    "developer_portal": {
        "label": "Developer Portal",
        "description": "Self-service MCP integration catalogue, API key generation, and Agent Playground.",
        "route": "/developer-portal",
    },
}

DEFAULT_FEATURE_FLAGS: dict[str, bool] = {key: True for key in FEATURE_DEFINITIONS}


def _stored_flags(tenant: Tenant) -> dict[str, bool]:
    flags_attr = getattr(tenant, "feature_flags", None)
    raw = flags_attr if isinstance(flags_attr, dict) else {}
    return {key: bool(raw[key]) for key in FEATURE_DEFINITIONS if key in raw}


def _stored_policy(tenant: Tenant) -> dict[str, dict[str, bool]]:
    policy_attr = getattr(tenant, "feature_policy", None)
    raw = policy_attr if isinstance(policy_attr, dict) else {}
    policy: dict[str, dict[str, bool]] = {}
    for key in FEATURE_DEFINITIONS:
        entry = raw.get(key) if isinstance(raw.get(key), dict) else {}
        policy[key] = {"tenant_editable": bool(entry.get("tenant_editable", False))}
    return policy


def resolve_feature_flags(tenant: Tenant) -> dict[str, bool]:
    flags = dict(DEFAULT_FEATURE_FLAGS)
    flags.update(_stored_flags(tenant))
    if getattr(tenant, "qa_dashboard_enabled", None) is False:
        flags["qa_dashboard"] = False
    if getattr(tenant, "mcp_portal_enabled", None) is False:
        flags["developer_portal"] = False
    return flags


def resolve_feature_policy(tenant: Tenant) -> dict[str, dict[str, bool]]:
    return _stored_policy(tenant)


def feature_flags_for_api(tenant: Tenant) -> dict[str, bool]:
    return resolve_feature_flags(tenant)


def feature_policy_for_api(tenant: Tenant) -> dict[str, dict[str, bool]]:
    return resolve_feature_policy(tenant)


def is_feature_enabled(tenant: Tenant, feature_key: str) -> bool:
    if feature_key not in FEATURE_DEFINITIONS:
        return True
    return resolve_feature_flags(tenant).get(feature_key, True)


def tenant_can_edit_feature(tenant: Tenant, feature_key: str) -> bool:
    if feature_key not in FEATURE_DEFINITIONS:
        return False
    policy = resolve_feature_policy(tenant)
    return policy.get(feature_key, {}).get("tenant_editable", False)


def apply_platform_feature_updates(
    tenant: Tenant,
    updates: dict[str, bool | None],
    *,
    tenant_editable: dict[str, bool | None] | None = None,
) -> None:
    flags = dict(tenant.feature_flags or {})
    policy = dict(tenant.feature_policy or {})
    for key, value in updates.items():
        if key not in FEATURE_DEFINITIONS or value is None:
            continue
        flags[key] = bool(value)
        entry = dict(policy.get(key) or {})
        if value is False:
            entry["tenant_editable"] = False
        elif tenant_editable and key in tenant_editable and tenant_editable[key] is not None:
            entry["tenant_editable"] = bool(tenant_editable[key])
        elif "tenant_editable" not in entry:
            entry["tenant_editable"] = False
        policy[key] = entry
    tenant.feature_flags = flags
    tenant.feature_policy = policy
    if "qa_dashboard" in updates and updates["qa_dashboard"] is not None:
        tenant.qa_dashboard_enabled = bool(updates["qa_dashboard"])
    if "developer_portal" in updates and updates["developer_portal"] is not None:
        tenant.mcp_portal_enabled = bool(updates["developer_portal"])


def apply_tenant_feature_update(tenant: Tenant, feature_key: str, enabled: bool) -> None:
    if feature_key not in FEATURE_DEFINITIONS:
        raise ValueError(f"Unknown feature '{feature_key}'")
    if not tenant_can_edit_feature(tenant, feature_key):
        raise PermissionError(f"Feature '{feature_key}' is managed by the platform operator")
    flags = dict(tenant.feature_flags or {})
    flags[feature_key] = bool(enabled)
    tenant.feature_flags = flags


def features_summary() -> list[dict[str, str]]:
    return [
        {"key": key, "label": meta["label"], "description": meta["description"], "route": meta["route"]}
        for key, meta in FEATURE_DEFINITIONS.items()
    ]
