from types import SimpleNamespace

import pytest

from app.services.tenant_provision_service import validate_tenant_slug


def test_validate_tenant_slug_accepts_valid() -> None:
    validate_tenant_slug("acme-corp")


@pytest.mark.parametrize("slug", ["Platform", "admin", "api", "bad slug", "-acme", "acme-"])
def test_validate_tenant_slug_rejects_invalid(slug: str) -> None:
    with pytest.raises(ValueError):
        validate_tenant_slug(slug)


def test_validate_tenant_slug_rejects_reserved() -> None:
    with pytest.raises(ValueError, match="reserved"):
        validate_tenant_slug("platform")
