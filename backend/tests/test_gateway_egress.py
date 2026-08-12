from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import uuid
from app.schemas.openai import (
    ChatCompletionRequest,
    ChatMessage,
    InspectionResult,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionUsage,
    PolicyViolation,
)
from app.services.gateway_context import GatewayContext
from app.services.gateway_service import process_chat_completion, PreparedChat
from app.services.integration_service import GatewayConfig


@pytest.mark.anyio
async def test_process_chat_completion_egress_redaction():
    mock_db = AsyncMock()
    mock_tenant_id = uuid.uuid4()
    ctx = GatewayContext(tenant_id=mock_tenant_id, actor="user@test.com")

    request = ChatCompletionRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="Tell me a secret")]
    )

    prepared = PreparedChat(
        messages=request.messages,
        routed_model="gpt-4o",
        upstream="mock",
        config=GatewayConfig(
            openai_api_key=None,
            gemini_api_key=None,
            gemini_default_model="gemini-1.5-pro",
            ollama_enabled=False,
            ollama_base_url="http://localhost:11434",
            ollama_default_model="llama3.2",
            source="environment"
        ),
        ingress=InspectionResult(allowed=True, action="allow", violations=[], risk="low"),
        combined="Tell me a secret"
    )

    # Simulated LLM response containing a US SSN
    mock_llm_response = ChatCompletionResponse(
        id="chatcmpl-test",
        created=123456,
        model="gpt-4o",
        choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content="Here is SSN: 000-12-3456"))],
        usage=ChatCompletionUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        pysetu={}
    )

    tenant_mock = MagicMock()
    tenant_mock.ai_token_limit_tpm = None
    tenant_mock.ai_token_limit_tph = None
    tenant_mock.ai_token_limit_tpd = None

    db_execute_mock = MagicMock()
    db_execute_mock.scalar_one.return_value = tenant_mock
    mock_db.execute = AsyncMock(return_value=db_execute_mock)

    async def mock_load_bundle(db, bundle_id):
        return None

    async def mock_get_default_bundle(db, tenant_id):
        return None

    with patch("app.services.gateway_service.prepare_chat_request", return_value=(prepared, prepared.ingress, None)), \
         patch("app.services.gateway_service._execute_upstream", return_value=mock_llm_response), \
         patch("app.services.gateway_service._load_bundle", side_effect=mock_load_bundle), \
         patch("app.services.policy_engine.get_tenant_default_bundle", side_effect=mock_get_default_bundle), \
         patch("app.services.gateway_service.record_provider_request", new_callable=AsyncMock), \
         patch("app.services.gateway_service._write_audit", new_callable=AsyncMock):

        serialized, ingress, error = await process_chat_completion(request, ctx, mock_db)

        assert error is None
        assert serialized is not None
        # SSN should be redacted in output content
        assert "000-12-3456" not in serialized["choices"][0]["message"]["content"]
        assert "[REDACTED]" in serialized["choices"][0]["message"]["content"]


@pytest.mark.anyio
async def test_process_chat_completion_egress_block():
    mock_db = AsyncMock()
    mock_tenant_id = uuid.uuid4()
    ctx = GatewayContext(tenant_id=mock_tenant_id, actor="user@test.com")

    request = ChatCompletionRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="Generate malicious payload")]
    )

    prepared = PreparedChat(
        messages=request.messages,
        routed_model="gpt-4o",
        upstream="mock",
        config=GatewayConfig(
            openai_api_key=None,
            gemini_api_key=None,
            gemini_default_model="gemini-1.5-pro",
            ollama_enabled=False,
            ollama_base_url="http://localhost:11434",
            ollama_default_model="llama3.2",
            source="environment"
        ),
        ingress=InspectionResult(allowed=True, action="allow", violations=[], risk="low"),
        combined="Generate malicious payload"
    )

    mock_llm_response = ChatCompletionResponse(
        id="chatcmpl-test",
        created=123456,
        model="gpt-4o",
        choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content="Malicious output"))],
        usage=ChatCompletionUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        pysetu={}
    )

    blocked_egress = InspectionResult(
        allowed=False,
        action="block",
        violations=[PolicyViolation(rule_name="Egress Block", detail="Output blocked", action="block", severity="high")],
        risk="high"
    )

    async def mock_load_bundle(db, bundle_id):
        return None

    async def mock_inspect_for_gateway(db, tenant_id, bundle, content, context=None):
        return blocked_egress

    with patch("app.services.gateway_service.prepare_chat_request", return_value=(prepared, prepared.ingress, None)), \
         patch("app.services.gateway_service._execute_upstream", return_value=mock_llm_response), \
         patch("app.services.gateway_service._load_bundle", side_effect=mock_load_bundle), \
         patch("app.services.gateway_service.inspect_for_gateway", side_effect=mock_inspect_for_gateway), \
         patch("app.services.gateway_service.record_provider_request", new_callable=AsyncMock), \
         patch("app.services.gateway_service._dispatch_gateway_block_alert", new_callable=AsyncMock) as mock_alert, \
         patch("app.services.gateway_service._write_audit", new_callable=AsyncMock):

        serialized, egress, error = await process_chat_completion(request, ctx, mock_db)

        assert serialized is None
        assert egress.allowed is False
        assert error == "Response blocked by PySetu egress inspection."
        mock_alert.assert_called_once()
