"""Tests for dependency health aggregation."""

import asyncio

import pytest

from app.services.health_service import build_dependency_status


def test_build_dependency_status_includes_database(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_db_health(_db=None):
        return True, None

    async def fake_opa_health():
        return True, None

    monkeypatch.setattr("app.services.health_service.check_database_health", fake_db_health)
    monkeypatch.setattr("app.services.health_service.check_opa_health", fake_opa_health)

    result = asyncio.run(build_dependency_status())
    assert result["status"] == "healthy"
    assert result["dependencies"]["database"]["status"] == "up"
    assert result["dependencies"]["opa"]["status"] in {"up", "disabled"}
