import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.governance import RoutingGroup
from app.services.llm_router import select_model, pick_routing_group_member


def test_pick_routing_group_member_failover():
    members = [
        {"model": "gemini-1.5-pro", "priority": 2, "weight": 50},
        {"model": "gpt-4o", "priority": 1, "weight": 50},
    ]
    chosen = pick_routing_group_member(members, strategy="failover")
    assert chosen == "gpt-4o"


def test_pick_routing_group_member_weighted():
    members = [
        {"model": "gpt-4o", "priority": 1, "weight": 100},
        {"model": "gemini-1.5-pro", "priority": 2, "weight": 0},
    ]
    chosen = pick_routing_group_member(members, strategy="weighted")
    assert chosen == "gpt-4o"


@pytest.mark.anyio
async def test_select_model_resolves_routing_group():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()

    group = RoutingGroup(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="production",
        description="",
        strategy="failover",
        members=[
            {"model": "gpt-4o", "priority": 1, "weight": 100},
            {"model": "gemini-1.5-pro", "priority": 2, "weight": 0},
        ],
        status="active",
    )

    # First db.execute for LLMProvider returns empty list, second db.execute for RoutingGroup returns [group]
    providers_mock = MagicMock()
    providers_mock.scalars.return_value.all.return_value = []

    groups_mock = MagicMock()
    groups_mock.scalars.return_value.all.return_value = [group]

    keys_mock = MagicMock()
    keys_mock.all.return_value = []

    mock_db.execute.side_effect = [keys_mock, providers_mock, groups_mock]

    decision = await select_model(
        requested_model="production",
        db=mock_db,
        tenant_id=tenant_id,
    )

    assert decision.model == "gpt-4o"
    assert decision.matched_rule == "production"
    assert decision.strategy == "routing_group"
