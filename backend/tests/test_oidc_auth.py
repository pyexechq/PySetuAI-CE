from app.services.oidc_auth_service import generate_pkce_pair, is_oidc_jit_provision_enabled, resolve_role_from_claims


def test_generate_pkce_pair_is_url_safe() -> None:
    verifier, challenge = generate_pkce_pair()
    assert len(verifier) > 20
    assert "=" not in challenge
    assert len(challenge) >= 43


def test_resolve_role_from_group_mapping() -> None:
    role = resolve_role_from_claims(
        {"groups": ["Security-Admins", "All-Staff"]},
        role_claim="groups",
        role_mapping={"Security-Admins": "security_admin"},
        default_role="developer",
    )
    assert role == "security_admin"


def test_resolve_role_falls_back_to_default() -> None:
    role = resolve_role_from_claims(
        {"groups": ["Unknown"]},
        role_claim="groups",
        role_mapping={"Security-Admins": "security_admin"},
        default_role="auditor",
    )
    assert role == "auditor"


def test_jit_enabled_when_tenant_toggle_on() -> None:
    from types import SimpleNamespace

    tenant = SimpleNamespace(oidc_jit_provision_enabled=True)
    assert is_oidc_jit_provision_enabled(tenant) is True


def test_jit_disabled_when_tenant_toggle_off() -> None:
    from types import SimpleNamespace

    tenant = SimpleNamespace(oidc_jit_provision_enabled=False)
    assert is_oidc_jit_provision_enabled(tenant) is False


def test_resolve_role_uses_first_matching_group() -> None:
    role = resolve_role_from_claims(
        {"groups": ["All-Staff", "Security-Admins"]},
        role_claim="groups",
        role_mapping={"Security-Admins": "security_admin", "All-Staff": "auditor"},
        default_role="developer",
    )
    assert role == "auditor"
