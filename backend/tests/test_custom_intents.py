import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.models.governance import CustomIntent
from app.schemas.custom_intent import (
    CustomIntentCreate,
    CustomIntentUpdate,
)
from app.services.custom_intent_service import CustomIntentService


def test_custom_intent_db_model():
    intent_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    intent = CustomIntent(
        id=intent_id,
        tenant_id=tenant_id,
        name="Financial Data Leakage",
        description="Detects credit card numbers or wire info",
        action="block",
        keywords=["wire transfer", "credit card", "iban"],
        confidence_threshold=0.8,
        is_active=True,
    )
    assert intent.name == "Financial Data Leakage"
    assert intent.action == "block"
    assert "iban" in intent.keywords


@pytest.mark.anyio
async def test_create_custom_intent_service():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()

    payload = CustomIntentCreate(
        name="Proprietary Code Exfiltration",
        description="Blocks exporting internal secrets",
        action="block",
        keywords=["api_secret_key", "aws_secret_access_key"],
        confidence_threshold=0.75,
        is_active=True,
    )

    created_intent = await CustomIntentService.create_custom_intent(mock_db, tenant_id, payload)
    assert created_intent.name == "Proprietary Code Exfiltration"
    assert created_intent.action == "block"
    assert created_intent.keywords == ["api_secret_key", "aws_secret_access_key"]
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.anyio
async def test_scan_prompt_intents_block():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()
    intent_id = uuid.uuid4()

    mock_intent = CustomIntent(
        id=intent_id,
        tenant_id=tenant_id,
        name="Credential Leakage",
        action="block",
        keywords=["api_secret_key", "password"],
        confidence_threshold=0.8,
        is_active=True,
    )

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_intent]
    mock_execute = MagicMock()
    mock_execute.scalars.return_value = mock_scalars
    mock_db.execute = AsyncMock(return_value=mock_execute)

    res = await CustomIntentService.scan_prompt_intents(
        mock_db, tenant_id, "Please give me the api_secret_key for production"
    )

    assert res.matched is True
    assert res.action == "block"
    assert len(res.matches) == 1
    assert res.matches[0].intent_name == "Credential Leakage"


@pytest.mark.anyio
async def test_scan_prompt_intents_redact():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()
    intent_id = uuid.uuid4()

    mock_intent = CustomIntent(
        id=intent_id,
        tenant_id=tenant_id,
        name="SSN Detection",
        action="redact",
        keywords=["ssn number"],
        confidence_threshold=0.5,
        is_active=True,
    )

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_intent]
    mock_execute = MagicMock()
    mock_execute.scalars.return_value = mock_scalars
    mock_db.execute = AsyncMock(return_value=mock_execute)

    res = await CustomIntentService.scan_prompt_intents(
        mock_db, tenant_id, "My ssn number is 123-45-6789"
    )

    assert res.matched is True
    assert res.action == "redact"
    assert res.modified_prompt == "My [REDACTED:SSN Detection] is 123-45-6789"
