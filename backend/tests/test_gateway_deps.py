import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.core import gateway_deps
from app.services.client_api_key_service import hash_client_key


def _request(origin: str | None = None) -> MagicMock:
    request = MagicMock()
    request.headers = {"origin": origin} if origin else {}
    return request


def _client_key_record(
    *,
    origins: list[str] | None = None,
    key_source: str = "pysetu",
    upstream_pass_through: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name="test-key",
        bundle_id=None,
        client_response_protocol=None,
        ai_rate_limit_rpm=None,
        ai_rate_limit_rph=None,
        ai_rate_limit_rpd=None,
        ai_token_limit_tpm=None,
        ai_token_limit_tph=None,
        ai_token_limit_tpd=None,
        token_saving_enabled=None,
        token_saving_mode=None,
        allowed_api_origins=origins,
        key_source=key_source,
        upstream_pass_through=upstream_pass_through,
        last_used_at=None,
    )


@pytest.mark.asyncio
async def test_get_gateway_context_enforces_per_key_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    record = _client_key_record(origins=["https://spa.example.com"])
    tenant = SimpleNamespace(allowed_api_origins=["https://tenant.example.com"])

    monkeypatch.setattr(gateway_deps, "resolve_client_api_key", AsyncMock(return_value=record))

    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: tenant))
    db.commit = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await gateway_deps.get_gateway_context(
            _request(origin="https://blocked.example.com"),
            SimpleNamespace(credentials="hg_test_key_value"),
            db,
        )
    assert exc.value.status_code == 403

    ctx = await gateway_deps.get_gateway_context(
        _request(origin="https://spa.example.com"),
        SimpleNamespace(credentials="hg_test_key_value"),
        db,
    )
    assert ctx.client_api_key_name == "test-key"


@pytest.mark.asyncio
async def test_get_gateway_context_sets_ingress_token_for_mirrored_pass_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = "sk-test-key-12345678"
    record = _client_key_record(key_source="mirrored", upstream_pass_through=True)
    tenant = SimpleNamespace(allowed_api_origins=None)

    monkeypatch.setattr(gateway_deps, "resolve_client_api_key", AsyncMock(return_value=record))

    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: tenant))
    db.commit = AsyncMock()

    ctx = await gateway_deps.get_gateway_context(
        _request(),
        SimpleNamespace(credentials=raw),
        db,
    )
    assert ctx.key_source == "mirrored"
    assert ctx.upstream_pass_through is True
    assert ctx.ingress_bearer_token == raw


@pytest.mark.asyncio
async def test_get_gateway_context_rejects_opaque_non_key_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gateway_deps, "resolve_client_api_key", AsyncMock(return_value=None))
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await gateway_deps.get_gateway_context(
            _request(),
            SimpleNamespace(credentials="not-a-jwt-or-key"),
            db,
        )
    assert exc.value.status_code == 401
