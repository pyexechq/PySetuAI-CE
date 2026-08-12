import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.governance import PromptTemplate, PromptVersion
from app.schemas.openai import ChatMessage
from app.services.prompt_injection_service import (
    apply_variable_substitution,
    resolve_and_inject_prompt,
)


def test_apply_variable_substitution():
    tmpl = "You are a customer service bot for {{ company_name }}. Help user {{ user_id }}."
    res = apply_variable_substitution(tmpl, {"company_name": "Acme Corp", "user_id": "U-123"})
    assert res == "You are a customer service bot for Acme Corp. Help user U-123."

    res_partial = apply_variable_substitution(tmpl, {"company_name": "Acme Corp"})
    assert res_partial == "You are a customer service bot for Acme Corp. Help user ."


@pytest.mark.anyio
async def test_resolve_and_inject_prompt_matched():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()
    template_id = uuid.uuid4()

    version_obj = PromptVersion(
        id=uuid.uuid4(),
        template_id=template_id,
        version=1,
        system_prompt="You are a verified support agent for {{ company }}.",
        variables=["company"],
    )

    template_obj = PromptTemplate(
        id=template_id,
        tenant_id=tenant_id,
        name="Support Prompt",
        alias="support-v1",
        enforce_mode="strict",
        is_active=True,
        current_version_id=version_obj.id,
        versions=[version_obj],
    )

    db_execute_mock = MagicMock()
    db_execute_mock.scalars.return_value.all.return_value = [template_obj]
    mock_db.execute = AsyncMock(return_value=db_execute_mock)

    messages = [
        ChatMessage(role="system", content="Ad-hoc system prompt"),
        ChatMessage(role="user", content="Help me with login"),
    ]

    new_messages, tmpl_id, ver_num, enf_mode, warning, is_blocked = await resolve_and_inject_prompt(
        mock_db,
        tenant_id,
        messages,
        requested_template="support-v1",
        variables={"company": "Globex"},
    )

    assert is_blocked is False
    assert tmpl_id == str(template_id)
    assert ver_num == 1
    assert enf_mode == "strict"
    assert new_messages[0].role == "system"
    assert new_messages[0].content == "You are a verified support agent for Globex."


@pytest.mark.anyio
async def test_resolve_and_inject_prompt_strict_mode_blocks_adhoc():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()

    template_obj = PromptTemplate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Strict Policy Template",
        enforce_mode="strict",
        is_active=True,
        versions=[],
    )

    db_execute_mock = MagicMock()
    db_execute_mock.scalars.return_value.all.return_value = [template_obj]
    mock_db.execute = AsyncMock(return_value=db_execute_mock)

    messages = [
        ChatMessage(role="system", content="Ad-hoc prompt"),
        ChatMessage(role="user", content="Hello"),
    ]

    new_messages, tmpl_id, ver_num, enf_mode, warning, is_blocked = await resolve_and_inject_prompt(
        mock_db,
        tenant_id,
        messages,
        requested_template=None,
    )

    assert is_blocked is True
    assert enf_mode == "strict"
    assert "blocked by tenant policy" in warning
