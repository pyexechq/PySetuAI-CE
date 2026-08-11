"""Tenant feature flag resolution and platform/tenant update rules."""

from types import SimpleNamespace

import pytest

from app.services.tenant_features_service import (
    apply_platform_feature_updates,
    apply_tenant_feature_update,
    feature_flags_for_api,
    feature_policy_for_api,
    is_feature_enabled,
    tenant_can_edit_feature,
)


def _tenant(**overrides):
    base = {
        "qa_dashboard_enabled": True,
        "feature_flags": {},
        "feature_policy": {},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_default_features_enabled() -> None:
    tenant = _tenant()
    flags = feature_flags_for_api(tenant)
    assert flags["qa_dashboard"] is True
    assert flags["compatibility_center"] is True
    assert flags["governance_sandbox"] is True
    assert flags["reports"] is True


def test_default_features_are_not_tenant_editable() -> None:
    tenant = _tenant()
    policy = feature_policy_for_api(tenant)
    for key in policy:
        assert policy[key]["tenant_editable"] is False
        assert tenant_can_edit_feature(tenant, key) is False


def test_legacy_qa_dashboard_column_respected() -> None:
    tenant = _tenant(qa_dashboard_enabled=False)
    assert is_feature_enabled(tenant, "qa_dashboard") is False


def test_platform_disable_makes_feature_non_editable() -> None:
    tenant = _tenant()
    apply_platform_feature_updates(tenant, {"reports": False})
    policy = feature_policy_for_api(tenant)
    assert feature_flags_for_api(tenant)["reports"] is False
    assert policy["reports"]["tenant_editable"] is False
    assert tenant_can_edit_feature(tenant, "reports") is False


def test_tenant_cannot_override_platform_locked_feature() -> None:
    tenant = _tenant()
    apply_platform_feature_updates(tenant, {"qa_dashboard": False})
    with pytest.raises(PermissionError):
        apply_tenant_feature_update(tenant, "qa_dashboard", True)
    assert is_feature_enabled(tenant, "qa_dashboard") is False


def test_tenant_cannot_toggle_platform_managed_features() -> None:
    tenant = _tenant()
    with pytest.raises(PermissionError):
        apply_tenant_feature_update(tenant, "governance_sandbox", False)


def test_platform_can_restore_tenant_editability_when_explicit() -> None:
    tenant = _tenant()
    apply_platform_feature_updates(tenant, {"compatibility_center": False})
    apply_platform_feature_updates(
        tenant,
        {"compatibility_center": True},
        tenant_editable={"compatibility_center": True},
    )
    assert tenant_can_edit_feature(tenant, "compatibility_center") is True
