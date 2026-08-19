import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.client_api_key_service import (
    KEY_SOURCE_MIRRORED,
    hash_client_key,
    looks_like_jwt,
    register_mirrored_client_key,
    resolve_client_api_key,
)


class _Scalars:
    def __init__(self, value) -> None:
        self._value = value

    def one_or_none(self):
        return self._value


class _ExecuteResult:
    def __init__(self, value) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return _Scalars(self._value)


class _FakeDb:
    def __init__(self, results: list) -> None:
        self._results = list(results)
        self.added: list = []

    async def execute(self, _query):
        if not self._results:
            return _ExecuteResult(None)
        return self._results.pop(0)

    def add(self, record) -> None:
        self.added.append(record)


def test_looks_like_jwt() -> None:
    assert looks_like_jwt("aaa.bbb.ccc")
    assert not looks_like_jwt("sk-test-key")
    assert not looks_like_jwt("hg_demo_key")


@pytest.mark.asyncio
async def test_resolve_client_api_key_accepts_non_hg_prefix() -> None:
    raw = "sk-test-key-12345678"
    record = SimpleNamespace(
        id=uuid.uuid4(),
        key_hash=hash_client_key(raw),
        is_active=True,
        last_used_at=None,
    )
    db = _FakeDb([_ExecuteResult(record)])
    resolved = await resolve_client_api_key(db, raw)
    assert resolved is record
    assert resolved.last_used_at is not None


@pytest.mark.asyncio
async def test_resolve_client_api_key_returns_none_when_missing() -> None:
    db = _FakeDb([_ExecuteResult(None)])
    assert await resolve_client_api_key(db, "sk-missing-key-123456") is None


@pytest.mark.asyncio
async def test_register_mirrored_client_key_rejects_duplicate() -> None:
    db = _FakeDb([_ExecuteResult(uuid.uuid4())])
    with pytest.raises(HTTPException) as exc:
        await register_mirrored_client_key(
            db,
            uuid.uuid4(),
            name="prod",
            raw_key="sk-test-key-12345678",
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_register_mirrored_client_key_creates_record() -> None:
    db = _FakeDb([_ExecuteResult(None)])
    record = await register_mirrored_client_key(
        db,
        uuid.uuid4(),
        name="prod",
        raw_key="sk-test-key-12345678",
        upstream_pass_through=True,
    )
    assert record.key_source == KEY_SOURCE_MIRRORED
    assert record.upstream_pass_through is True
    assert record.key_hash == hash_client_key("sk-test-key-12345678")
    assert len(db.added) == 1
