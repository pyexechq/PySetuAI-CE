"""Tests for UAG client response serialization."""

from app.modules.uag.client_response import resolve_client_response_protocol, serialize_gateway_response
from app.modules.uag.model_mapping import normalize_target_provider
from app.schemas.openai import ChatCompletionChoice, ChatCompletionResponse, ChatCompletionUsage, ChatMessage


def _sample_response(*, with_metadata: bool = True) -> ChatCompletionResponse:
    return ChatCompletionResponse(
        id="chatcmpl-test",
        created=123,
        model="llama3.2",
        choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content="Hello"))],
        usage=ChatCompletionUsage(prompt_tokens=3, completion_tokens=2, total_tokens=5),
        helixguard={"upstream": "ollama"} if with_metadata else None,
    )


def test_openai_response_strips_helixguard_by_default() -> None:
    body = serialize_gateway_response("openai", _sample_response(), None, None, include_metadata=False)
    assert body["object"] == "chat.completion"
    assert "helixguard" not in body
    assert body["choices"][0]["message"]["content"] == "Hello"


def test_openai_response_can_include_metadata() -> None:
    body = serialize_gateway_response("openai", _sample_response(), None, None, include_metadata=True)
    assert body["helixguard"]["upstream"] == "ollama"


def test_gemini_response_shape() -> None:
    body = serialize_gateway_response("gemini", _sample_response(), None, None, include_metadata=False)
    assert "candidates" in body
    assert body["candidates"][0]["content"]["parts"][0]["text"] == "Hello"
    assert body["usageMetadata"]["totalTokenCount"] == 5
    assert "choices" not in body


def test_anthropic_response_shape() -> None:
    body = serialize_gateway_response("anthropic", _sample_response(), None, None, include_metadata=False)
    assert body["type"] == "message"
    assert body["content"][0]["text"] == "Hello"
    assert body["usage"]["output_tokens"] == 2


def test_normalize_target_provider_maps_custom_to_openai() -> None:
    assert normalize_target_provider("custom") == "openai"
    assert normalize_target_provider("ollama") == "ollama"


def test_api_key_protocol_overrides_tenant_default() -> None:
    assert (
        resolve_client_response_protocol(
            mapping_protocol=None,
            api_key_protocol="gemini",
            tenant_protocol="openai",
        )
        == "gemini"
    )


def test_mapping_protocol_overrides_api_key() -> None:
    assert (
        resolve_client_response_protocol(
            mapping_protocol="anthropic",
            api_key_protocol="gemini",
            tenant_protocol="openai",
        )
        == "anthropic"
    )


def test_inherit_api_key_uses_tenant_default() -> None:
    assert (
        resolve_client_response_protocol(
            mapping_protocol=None,
            api_key_protocol="inherit",
            tenant_protocol="anthropic",
        )
        == "anthropic"
    )


def test_protocol_source_resolution() -> None:
    from app.modules.uag.client_response import resolve_client_response_protocol_with_source

    assert resolve_client_response_protocol_with_source(
        mapping_protocol="gemini",
        api_key_protocol="anthropic",
        tenant_protocol="openai",
    ) == ("gemini", "mapping")
    assert resolve_client_response_protocol_with_source(
        mapping_protocol=None,
        api_key_protocol="anthropic",
        tenant_protocol="openai",
    ) == ("anthropic", "api_key")
    assert resolve_client_response_protocol_with_source(
        mapping_protocol=None,
        api_key_protocol=None,
        tenant_protocol="openai",
    ) == ("openai", "tenant")
