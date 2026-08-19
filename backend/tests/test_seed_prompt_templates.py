import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.seed_prompt_templates import DEMO_PROMPT_TEMPLATES, seed_prompt_templates_for_tenant
from app.models.governance import PromptTemplate


@pytest.mark.anyio
async def test_seed_prompt_templates_for_tenant_inserts_samples():
    mock_session = AsyncMock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=existing_result)

    created = await seed_prompt_templates_for_tenant(mock_session, uuid.uuid4())

    assert created is True
    assert mock_session.add.call_count == len(DEMO_PROMPT_TEMPLATES) * 2
    assert mock_session.flush.await_count >= len(DEMO_PROMPT_TEMPLATES) * 2


@pytest.mark.anyio
async def test_seed_prompt_templates_for_tenant_skips_when_present():
    mock_session = AsyncMock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = PromptTemplate(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name="Existing",
        enforce_mode="warn",
        is_active=True,
    )
    mock_session.execute = AsyncMock(return_value=existing_result)

    created = await seed_prompt_templates_for_tenant(mock_session, uuid.uuid4())

    assert created is False
    mock_session.add.assert_not_called()
