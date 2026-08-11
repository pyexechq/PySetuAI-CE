"""Extended UAG tests — functional, security, and performance."""

import time

from app.modules.uag.canonical import build_canonical_from_openai
from app.modules.uag.protocol_translator import ProtocolTranslator
from app.modules.uag.provider_registry import compatibility_score, get_provider
from app.modules.uag.translators.claude import ClaudeTranslator
from app.modules.uag.translators.gemini import GeminiTranslator
from app.modules.uag.translators.openai import OpenAITranslator
from app.schemas.openai import ChatCompletionRequest, ChatMessage


def test_openai_to_canonical_normalization() -> None:
    request = ChatCompletionRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="Hello")],
    )
    canonical = build_canonical_from_openai(request, tenant_id="tenant-1")
    assert canonical.source_protocol == "openai"
    assert canonical.requested_model == "gpt-4o"
    assert canonical.text_for_inspection() == "Hello"


def test_gemini_translator_builds_contents_payload() -> None:
    request = ChatCompletionRequest(
        model="gemini-1.5-pro",
        messages=[
            ChatMessage(role="system", content="You are helpful"),
            ChatMessage(role="user", content="Hi"),
        ],
    )
    canonical = build_canonical_from_openai(
        request,
        tenant_id="tenant-1",
        target_provider="gemini",
        target_protocol="gemini",
    )
    translator = GeminiTranslator()
    payload = translator.translate_to_upstream(canonical)
    assert "contents" in payload
    assert payload["systemInstruction"]["parts"][0]["text"] == "You are helpful"


def test_claude_translator_builds_messages_payload() -> None:
    request = ChatCompletionRequest(
        model="claude-sonnet-4",
        messages=[
            ChatMessage(role="system", content="Be concise"),
            ChatMessage(role="user", content="Summarize"),
        ],
    )
    canonical = build_canonical_from_openai(
        request,
        tenant_id="tenant-1",
        target_provider="claude",
        target_protocol="anthropic",
    )
    payload = ClaudeTranslator().translate_to_upstream(canonical)
    assert payload["system"] == "Be concise"
    assert payload["messages"][0]["content"] == "Summarize"


def test_openai_response_passthrough_keeps_requested_model() -> None:
    request = ChatCompletionRequest(model="gpt-4o", messages=[ChatMessage(role="user", content="Hi")])
    canonical = build_canonical_from_openai(request, tenant_id="tenant-1")
    translator = OpenAITranslator()
    response = translator.translate_response(
        canonical,
        {
            "id": "chatcmpl-test",
            "created": 1,
            "model": "gemini-1.5-pro",
            "choices": [{"message": {"role": "assistant", "content": "Hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    )
    assert response.model == "gpt-4o"
    assert response.choices[0].message.content == "Hello"


def test_compatibility_score_openai_to_gemini() -> None:
    assert compatibility_score("openai", "gemini") >= 0.95


def test_provider_registry_resolves_ollama() -> None:
    provider = get_provider("ollama")
    assert provider is not None
    assert provider.protocol == "openai-compatible"


def test_protocol_translator_detects_openai_path() -> None:
    translator = ProtocolTranslator(source_protocol="openai")
    assert translator.detect_protocol("/v1/chat/completions") == "openai"


def test_canonical_includes_pii_for_inspection() -> None:
    request = ChatCompletionRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="SSN 123-45-6789")],
    )
    canonical = build_canonical_from_openai(request, tenant_id="tenant-1")
    assert "123-45-6789" in canonical.text_for_inspection()


def test_openai_to_gemini_translation_under_50ms() -> None:
    request = ChatCompletionRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="Hello")],
    )
    canonical = build_canonical_from_openai(
        request,
        tenant_id="tenant-1",
        target_provider="gemini",
        target_protocol="gemini",
    )
    translator = ProtocolTranslator(source_protocol="openai")
    started = time.perf_counter()
    payload, trace = translator.translate_request(canonical)
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert "contents" in payload
    assert trace.compatibility_score is not None
    assert elapsed_ms < 50
