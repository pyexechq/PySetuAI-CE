import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.governance import _validate_routing_target_model


def _db_with_active_providers(*names: str) -> AsyncMock:
    result = MagicMock()
    result.all.return_value = [(name,) for name in names]
    db = AsyncMock()
    db.execute.return_value = result
    return db


@pytest.mark.anyio
async def test_routing_target_pool_matches_active_registered_providers() -> None:
    target_model = await _validate_routing_target_model(
        _db_with_active_providers("GPT-4o", "Claude 3.5 Sonnet"),
        uuid.uuid4(),
        "gpt-4o, claude 3.5 sonnet",
    )

    assert target_model == "GPT-4o, Claude 3.5 Sonnet"


@pytest.mark.anyio
async def test_routing_target_rejects_unknown_or_inactive_provider() -> None:
    with pytest.raises(HTTPException, match="active registered LLM provider") as exc_info:
        await _validate_routing_target_model(
            _db_with_active_providers("GPT-4o"),
            uuid.uuid4(),
            "GPT-4o, Archived Claude",
        )

    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_routing_target_rejects_empty_pool_member() -> None:
    with pytest.raises(HTTPException, match="active registered LLM provider"):
        await _validate_routing_target_model(
            _db_with_active_providers("GPT-4o"),
            uuid.uuid4(),
            "GPT-4o,",
        )