"""Tests for tenant response and feature wiring."""

from types import SimpleNamespace

from app.services.tenant_provision_service import tenant_response_dict


def test_tenant_response_dict_includes_features() -> None:
    tenant = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        name="Globex",
        slug="globex",
        is_active=True,
        created_at=None,
        subdomain="globex",
        entry_mode="login_only",
        feature_flags={"reports": False},
        feature_policy={"reports": {"tenant_editable": False}},
        qa_dashboard_enabled=True,
    )
    row = tenant_response_dict(tenant)
    assert row["features"]["reports"] is False
    assert row["features"]["qa_dashboard"] is True
    assert row["feature_policy"]["reports"]["tenant_editable"] is False
