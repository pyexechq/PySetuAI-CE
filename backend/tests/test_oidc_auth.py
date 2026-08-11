from app.services.oidc_auth_service import generate_pkce_pair, resolve_role_from_claims


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
