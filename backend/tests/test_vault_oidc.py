from app.services.oidc_provider_service import _normalize_role_mapping
from app.services.vault_service import is_insecure_jwt_secret


def test_normalize_role_mapping_accepts_valid_roles() -> None:
    mapping = _normalize_role_mapping({"Security-Admins": "security_admin", "Devs": "developer"})
    assert mapping["Security-Admins"] == "security_admin"
    assert mapping["Devs"] == "developer"


def test_normalize_role_mapping_rejects_unknown_role() -> None:
    try:
        _normalize_role_mapping({"Bad": "superuser"})
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_insecure_jwt_secret_detects_defaults() -> None:
    assert is_insecure_jwt_secret("dev-secret-change-in-production")
    assert is_insecure_jwt_secret("change-me-in-production-use-vault")
    assert is_insecure_jwt_secret("change-me-in-production")
    assert is_insecure_jwt_secret("airgap-change-me-before-production")
    assert not is_insecure_jwt_secret("a-secure-random-production-secret-value")
