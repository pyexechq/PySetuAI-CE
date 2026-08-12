import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from app.models.governance import RoutingGroup
from app.schemas.openai import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
    InspectionResult,
)
from app.services.gateway_context import GatewayContext
from app.services.gateway_service import PreparedChat, process_chat_completion
from app.services.integration_service import GatewayConfig


@pytest.mark.anyio
async def test_auto_failover_success_on_second_candidate():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()
    ctx = GatewayContext(tenant_id=tenant_id, actor="user@test.com")

    request = ChatCompletionRequest(
        model="production",
        messages=[ChatMessage(role="user", content="Hello")]
    )

    prepared = PreparedChat(
        messages=request.messages,
        routed_model="primary-failed-model",
        upstream="openai",
        config=GatewayConfig(
            openai_api_key="sk-test",
            gemini_api_key=None,
            gemini_default_model="gemini-1.5-pro",
            ollama_enabled=False,
            ollama_base_url="http://localhost:11434",
            ollama_default_model="llama3.2",
            source="environment"
        ),
        ingress=InspectionResult(allowed=True, action="allow", violations=[], risk="low"),
        combined="Hello",
        matched_routing_rule="production",
        routing_strategy="routing_group"
    )

    group = RoutingGroup(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="production",
        description="",
        strategy="failover",
        members=[
            {"model": "primary-failed-model", "priority": 1, "weight": 100},
            {"model": "secondary-success-model", "priority": 2, "weight": 0},
        ],
        status="active"
    )

    mock_llm_response = ChatCompletionResponse(
        id="chatcmpl-fallback",
        created=123456,
        model="secondary-success-model",
        choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content="Fallback response"))],
        usage=ChatCompletionUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10),
        pysetu={}
    )

    tenant_mock = MagicMock()
    tenant_mock.ai_token_limit_tpm = None
    tenant_mock.ai_token_limit_tph = None
    tenant_mock.ai_token_limit_tpd = None

    async def mock_execute(query, *args, **kwargs):
        query_str = str(query)
        res = MagicMock()
        if "routing_groups" in query_str:
            res.scalar_one_or_none.return_value = group
        elif "policy_bundles" in query_str:
            res.scalar_one_or_none.return_value = None
            res.scalars.return_value.all.return_value = []
        elif "tenants" in query_str:
            res.scalar_one.return_value = tenant_mock
            res.scalar_one_or_none.return_value = tenant_mock
        else:
            res.scalar_one_or_none.return_value = None
            res.scalars.return_value.all.return_value = []
        return res

    mock_db.execute = AsyncMock(side_effect=mock_execute)

    async def mock_execute_upstream(prep, req):
        if prep.routed_model == "primary-failed-model":
            raise httpx.HTTPStatusError("503 Service Unavailable", request=MagicMock(), response=MagicMock(status_code=503))
        return mock_llm_response

    async def mock_load_bundle(db, bundle_id):
        return None

    with patch("app.services.gateway_service.prepare_chat_request", return_value=(prepared, prepared.ingress, None)), \
         patch("app.services.gateway_service._execute_upstream", side_effect=mock_execute_upstream), \
         patch("app.services.gateway_service._load_bundle", side_effect=mock_load_bundle), \
         patch("app.services.gateway_service.record_provider_request", new_callable=AsyncMock), \
         patch("app.services.gateway_service._write_audit", new_callable=AsyncMock) as mock_audit:

        serialized, ingress, error = await process_chat_completion(request, ctx, mock_db)

        assert error is None
        assert serialized is not None
        audit_details_arg = mock_audit.call_args[0][6]
        assert "failover_chain" in audit_details_arg
