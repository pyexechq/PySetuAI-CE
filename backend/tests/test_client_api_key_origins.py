import uuid
from types import SimpleNamespace

import pytest

from app.services.client_api_key_service import (
    allowed_api_origins_mode,
    hash_client_key,
    mirrored_key_prefix,
    resolve_effective_api_origins,
    validate_api_origins,
)


def _key(origins: list[str] | None) -> SimpleNamespace:
    return SimpleNamespace(allowed_api_origins=origins)


def _tenant(origins: list[str] | None) -> SimpleNamespace:
    return SimpleNamespace(allowed_api_origins=origins)


def test_resolve_effective_origins_inherit_tenant() -> None:
    assert resolve_effective_api_origins(_key(None), _tenant(["https://app.example.com"])) == [
        "https://app.example.com"
    ]


def test_resolve_effective_origins_inherit_empty_tenant() -> None:
    assert resolve_effective_api_origins(_key(None), _tenant(None)) is None
    assert resolve_effective_api_origins(_key(None), _tenant([])) is None


def test_resolve_effective_origins_key_allow_all_override() -> None:
    assert resolve_effective_api_origins(_key([]), _tenant(["https://app.example.com"])) is None


def test_resolve_effective_origins_key_restrict_override() -> None:
    assert resolve_effective_api_origins(_key(["https://spa.example.com"]), _tenant(["https://app.example.com"])) == [
        "https://spa.example.com"
    ]


def test_allowed_api_origins_mode_values() -> None:
    assert allowed_api_origins_mode(_key(None)) == "inherit"
    assert allowed_api_origins_mode(_key([])) == "allow_all"
    assert allowed_api_origins_mode(_key(["https://a.example.com"])) == "restrict"


def test_validate_api_origins_normalizes_and_dedupes() -> None:
    assert validate_api_origins(["https://app.example.com/", "https://app.example.com"]) == [
        "https://app.example.com"
    ]


def test_validate_api_origins_allow_all_sentinel() -> None:
    assert validate_api_origins([]) == []


def test_validate_api_origins_rejects_http_non_localhost() -> None:
    with pytest.raises(ValueError, match="https"):
        validate_api_origins(["http://app.example.com"])


def test_validate_api_origins_allows_localhost_http() -> None:
    assert validate_api_origins(["http://localhost:3000"]) == ["http://localhost:3000"]


def test_validate_api_origins_allows_chrome_extension() -> None:
    origin = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"
    assert validate_api_origins([origin]) == [origin]


def test_mirrored_key_prefix() -> None:
    assert mirrored_key_prefix("sk-proj-abcdefghijklmnop") == "sk-proj-abcd"


def test_hash_client_key_is_stable() -> None:
    assert hash_client_key("sk-test-key-12345678") == hash_client_key("sk-test-key-12345678")
    assert hash_client_key("sk-test-key-12345678") != hash_client_key("hg_other")
