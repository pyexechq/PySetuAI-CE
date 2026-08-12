import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.api.v1.gateway import _handle_chat_completions
from app.schemas.openai import ChatCompletionRequest, ChatMessage
from app.services.alert_webhook_service import build_gateway_alert_event
from app.services.gateway_context import GatewayContext


def test_build_gateway_alert_event_rate_limit_and_budget():
    rate_event = build_gateway_alert_event(
        action="gateway.rate_limit.block",
        actor="user@acme.com",
        resource="gpt-4o",
        status="blocked",
        risk="medium",
        details="Gateway request blocked by AI rate limit (RPM/RPH/RPD)",
    )
    assert rate_event["title"] == "AI rate limit exceeded"
    assert rate_event["action"] == "gateway.rate_limit.block"

    budget_event = build_gateway_alert_event(
        action="gateway.token_budget.block",
        actor="user@acme.com",
        resource="gpt-4o",
        status="blocked",
        risk="high",
        details="Gateway request blocked by AI token budget limit (TPM/TPH/TPD)",
    )
    assert budget_event["title"] == "AI token budget limit exceeded"
    assert budget_event["action"] == "gateway.token_budget.block"


@pytest.mark.anyio
async def test_gateway_dispatches_rate_limit_alert():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()
    ctx = GatewayContext(tenant_id=tenant_id, actor="user@acme.com")

    request = ChatCompletionRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="Hello")]
    )

    tenant_mock = MagicMock()
    tenant_mock.ai_rate_limit_rpm = 10
    tenant_mock.ai_rate_limit_rph = None
    tenant_mock.ai_rate_limit_rpd = None

    db_execute_mock = MagicMock()
    db_execute_mock.scalar_one.return_value = tenant_mock
    mock_db.execute = AsyncMock(return_value=db_execute_mock)

    with patch("app.api.v1.gateway.check_ai_rate_limits", return_value=(False, 30)), \
         patch("app.api.v1.gateway.dispatch_tenant_alerts", new_callable=AsyncMock) as mock_dispatch:

        response = await _handle_chat_completions(request, ctx, mock_db)
        assert response.status_code == 429
        mock_dispatch.assert_called_once()
        event_arg = mock_dispatch.call_args[0][2]
        assert event_arg["action"] == "gateway.rate_limit.block"


@pytest.mark.anyio
async def test_gateway_dispatches_token_budget_alert():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()
    ctx = GatewayContext(tenant_id=tenant_id, actor="user@acme.com")

    request = ChatCompletionRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="Hello")]
    )

    tenant_mock = MagicMock()
    tenant_mock.ai_rate_limit_rpm = None
    tenant_mock.ai_rate_limit_rph = None
    tenant_mock.ai_rate_limit_rpd = None
    tenant_mock.ai_token_limit_tpm = 100
    tenant_mock.ai_token_limit_tph = None
    tenant_mock.ai_token_limit_tpd = None

    db_execute_mock = MagicMock()
    db_execute_mock.scalar_one.return_value = tenant_mock
    mock_db.execute = AsyncMock(return_value=db_execute_mock)

    with patch("app.api.v1.gateway.check_ai_rate_limits", return_value=(True, 0)), \
         patch("app.api.v1.gateway.check_ai_token_limits", return_value=(False, 60)), \
         patch("app.api.v1.gateway.dispatch_tenant_alerts", new_callable=AsyncMock) as mock_dispatch:

        response = await _handle_chat_completions(request, ctx, mock_db)
        assert response.status_code == 429
        mock_dispatch.assert_called_once()
        event_arg = mock_dispatch.call_args[0][2]
        assert event_arg["action"] == "gateway.token_budget.block"
