import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.governance import PromptTemplate, PromptVersion
from app.schemas.prompt_template import PromptTemplateCreate, PromptTemplateUpdate, PromptVersionCreate
from app.services.prompt_template_service import (
    add_prompt_version,
    create_prompt_template,
    delete_prompt_template,
    extract_variables,
    get_prompt_template,
    list_prompt_templates,
    update_prompt_template,
)


def test_extract_variables():
    text = "Hello {{ user_name }}, your role is {{ role }} and department is {{ department }} (repeat {{ user_name }})."
    vars_extracted = extract_variables(text)
    assert vars_extracted == ["user_name", "role", "department"]


def test_prompt_template_db_model():
    template_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    template = PromptTemplate(
        id=template_id,
        tenant_id=tenant_id,
        name="Support Assistant",
        alias="support-v1",
        description="Default support prompt",
        enforce_mode="strict",
        is_active=True,
    )
    assert template.name == "Support Assistant"
    assert template.enforce_mode == "strict"
    assert template.is_active is True


@pytest.mark.anyio
async def test_create_prompt_template_service():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()

    payload = PromptTemplateCreate(
        name="System Prompt 1",
        alias="sys-1",
        description="Test prompt",
        enforce_mode="warn",
        system_prompt="You are a helpful assistant for {{ company_name }}.",
    )

    created_template = PromptTemplate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=payload.name,
        alias=payload.alias,
        description=payload.description,
        enforce_mode=payload.enforce_mode,
        is_active=True,
    )

    db_execute_mock = MagicMock()
    db_execute_mock.scalar_one.return_value = created_template
    mock_db.execute = AsyncMock(return_value=db_execute_mock)

    result = await create_prompt_template(mock_db, tenant_id, payload, created_by="admin@acme.com")
    assert result.name == "System Prompt 1"
    assert mock_db.add.call_count >= 2  # Added template and version
    assert mock_db.commit.called


@pytest.mark.anyio
async def test_add_prompt_version_service():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()
    template_id = uuid.uuid4()

    existing_template = PromptTemplate(
        id=template_id,
        tenant_id=tenant_id,
        name="System Prompt 1",
        enforce_mode="warn",
        is_active=True,
        versions=[],
    )

    db_execute_mock = MagicMock()
    db_execute_mock.scalar_one_or_none.return_value = existing_template
    mock_db.execute = AsyncMock(return_value=db_execute_mock)

    payload = PromptVersionCreate(system_prompt="Updated prompt for {{ company_name }} and {{ user_id }}.")
    version = await add_prompt_version(mock_db, tenant_id, template_id, payload, created_by="admin@acme.com")

    assert version.version == 1
    assert version.variables == ["company_name", "user_id"]
    assert mock_db.add.called
    assert mock_db.commit.called
