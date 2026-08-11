from types import SimpleNamespace

from app.services.tenant_branding_service import (
    DEFAULT_TAGLINE,
    branding_dict,
    public_branding_dict,
    resolve_display_name,
    resolve_tagline,
)


def _tenant(**overrides):
    base = {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "Acme Corporation",
        "slug": "acme",
        "display_name": None,
        "logo_url": None,
        "brand_tagline": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_resolve_display_name_uses_override() -> None:
    tenant = _tenant(display_name="Acme AI Platform")
    assert resolve_display_name(tenant) == "Acme AI Platform"


def test_resolve_display_name_falls_back_to_name() -> None:
    tenant = _tenant(display_name="  ")
    assert resolve_display_name(tenant) == "Acme Corporation"


def test_resolve_tagline_default() -> None:
    tenant = _tenant()
    assert resolve_tagline(tenant) == DEFAULT_TAGLINE


def test_public_branding_dict_shape() -> None:
    payload = public_branding_dict(_tenant(display_name="Acme Secure AI", brand_tagline="Governed AI"))
    assert payload["slug"] == "acme"
    assert payload["display_name"] == "Acme Secure AI"
    assert payload["brand_tagline"] == "Governed AI"


def test_branding_dict_includes_defaults() -> None:
    payload = branding_dict(_tenant())
    assert payload["display_name"] == "Acme Corporation"
    assert payload["default_product_name"] == "PySetu AI"
