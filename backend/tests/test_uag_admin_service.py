"""UAG admin service unit tests."""

import asyncio
from types import SimpleNamespace

from app.schemas.uag import UagModelMappingUpdateRequest, UagTranslationPolicyUpdateRequest
from app.services.uag_admin_service import mapping_to_dict, policy_to_dict, update_mapping, update_policy


def test_mapping_to_dict_includes_enabled() -> None:
    row = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        requested_model="gpt-4o",
        actual_model="gemini-1.5-pro",
        target_provider="gemini",
        emulate_protocol="openai",
        enabled=False,
    )
    data = mapping_to_dict(row)
    assert data["enabled"] is False


def test_policy_to_dict_includes_enabled() -> None:
    row = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000002",
        name="Finance route",
        conditions={"department": "finance"},
        actions={"route_to": "ollama"},
        priority=10,
        enabled=True,
    )
    data = policy_to_dict(row)
    assert data["enabled"] is True


def test_update_mapping_toggles_enabled() -> None:
    row = SimpleNamespace(
        requested_model="gpt-4o",
        actual_model="gemini-1.5-pro",
        target_provider="gemini",
        emulate_protocol="openai",
        enabled=True,
    )
    commits: list[bool] = []

    class FakeSession:
        async def commit(self) -> None:
            commits.append(True)

        async def refresh(self, _row) -> None:
            return None

    updated = asyncio.run(update_mapping(FakeSession(), row, {"enabled": False}))
    assert updated.enabled is False
    assert commits


def test_update_policy_toggles_enabled() -> None:
    row = SimpleNamespace(
        name="Finance route",
        conditions={"department": "finance"},
        actions={"route_to": "ollama"},
        priority=10,
        enabled=True,
    )
    commits: list[bool] = []

    class FakeSession:
        async def commit(self) -> None:
            commits.append(True)

        async def refresh(self, _row) -> None:
            return None

    updated = asyncio.run(update_policy(FakeSession(), row, {"enabled": False}))
    assert updated.enabled is False
    assert commits


def test_mapping_update_request_accepts_enabled_only() -> None:
    body = UagModelMappingUpdateRequest(enabled=False)
    assert body.model_dump(exclude_unset=True) == {"enabled": False}


def test_policy_update_request_accepts_enabled_only() -> None:
    body = UagTranslationPolicyUpdateRequest(enabled=True)
    assert body.model_dump(exclude_unset=True) == {"enabled": True}
