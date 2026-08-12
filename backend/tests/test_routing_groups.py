import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.governance import RoutingGroup
from app.schemas.routing_groups import RoutingGroupCreate, RoutingGroupMember, RoutingGroupUpdate


def test_routing_group_member_schema():
    member = RoutingGroupMember(model="gpt-4o", weight=70.0, priority=1)
    assert member.model == "gpt-4o"
    assert member.weight == 70.0
    assert member.priority == 1


def test_routing_group_create_schema():
    create = RoutingGroupCreate(
        name="production",
        description="Production models pool",
        strategy="weighted",
        members=[
            RoutingGroupMember(model="gpt-4o", weight=70.0, priority=1),
            RoutingGroupMember(model="gemini-1.5-pro", weight=30.0, priority=2),
        ],
    )
    assert create.name == "production"
    assert len(create.members) == 2
    assert create.members[0].model == "gpt-4o"


@pytest.mark.anyio
async def test_create_routing_group_db_model():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()

    group = RoutingGroup(
        tenant_id=tenant_id,
        name="production",
        description="Production models pool",
        strategy="weighted",
        members=[{"model": "gpt-4o", "weight": 70.0, "priority": 1}],
        status="active",
    )

    mock_db.add(group)
    mock_db.add.assert_called_once_with(group)
    assert group.name == "production"
    assert group.tenant_id == tenant_id
    assert group.members == [{"model": "gpt-4o", "weight": 70.0, "priority": 1}]
