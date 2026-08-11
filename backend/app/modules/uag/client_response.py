"""Serialize gateway responses in admin-selected client API shapes."""

from __future__ import annotations

from typing import Any

from app.modules.uag.canonical import CanonicalPrompt, TranslationTrace
from app.schemas.openai import ChatCompletionResponse

SUPPORTED_CLIENT_PROTOCOLS = frozenset({"openai", "gemini", "anthropic", "claude"})
INHERIT_CLIENT_PROTOCOL = "inherit"


def normalize_client_protocol(protocol: str) -> str:
    lowered = protocol.strip().lower()
    if lowered == "claude":
        return "anthropic"
    if lowered in SUPPORTED_CLIENT_PROTOCOLS:
        return lowered
    return "openai"


def resolve_client_response_protocol(
    *,
    mapping_protocol: str | None,
    api_key_protocol: str | None,
    tenant_protocol: str,
) -> str:
    protocol, _ = resolve_client_response_protocol_with_source(
        mapping_protocol=mapping_protocol,
        api_key_protocol=api_key_protocol,
        tenant_protocol=tenant_protocol,
    )
    return protocol


def resolve_client_response_protocol_with_source(
    *,
    mapping_protocol: str | None,
    api_key_protocol: str | None,
    tenant_protocol: str,
) -> tuple[str, str]:
    if mapping_protocol:
        return normalize_client_protocol(mapping_protocol), "mapping"
    if api_key_protocol and api_key_protocol.strip().lower() not in {"", INHERIT_CLIENT_PROTOCOL, "default", "auto"}:
        return normalize_client_protocol(api_key_protocol), "api_key"
    return normalize_client_protocol(tenant_protocol), "tenant"


def serialize_gateway_response(
    protocol: str,
    response: ChatCompletionResponse,
    canonical: CanonicalPrompt | None,
    trace: TranslationTrace | None,
    *,
    include_metadata: bool,
) -> dict[str, Any]:
    normalized = normalize_client_protocol(protocol)
    if normalized == "gemini":
        body = _serialize_gemini(response, canonical)
    elif normalized == "anthropic":
        body = _serialize_anthropic(response, canonical)
    else:
        body = _serialize_openai(response)

    if include_metadata and response.pysetu:
        body["pysetu"] = response.pysetu
    return body


def _serialize_openai(response: ChatCompletionResponse) -> dict[str, Any]:
    return response.model_dump(exclude_none=True, exclude={"pysetu"})


def _serialize_gemini(response: ChatCompletionResponse, canonical: CanonicalPrompt | None) -> dict[str, Any]:
    text = response.choices[0].message.content if response.choices else ""
    finish_reason = response.choices[0].finish_reason if response.choices else "stop"
    usage = response.usage
    model_version = canonical.requested_model if canonical else response.model
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": text}], "role": "model"},
                "finishReason": _map_gemini_finish_reason(finish_reason),
                "index": 0,
            }
        ],
        "usageMetadata": {
            "promptTokenCount": usage.prompt_tokens,
            "candidatesTokenCount": usage.completion_tokens,
            "totalTokenCount": usage.total_tokens,
        },
        "modelVersion": model_version,
    }


def _serialize_anthropic(response: ChatCompletionResponse, canonical: CanonicalPrompt | None) -> dict[str, Any]:
    text = response.choices[0].message.content if response.choices else ""
    usage = response.usage
    return {
        "id": response.id,
        "type": "message",
        "role": "assistant",
        "model": canonical.requested_model if canonical else response.model,
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
        },
    }


def _map_gemini_finish_reason(reason: str) -> str:
    mapping = {
        "stop": "STOP",
        "length": "MAX_TOKENS",
        "content_filter": "SAFETY",
    }
    return mapping.get(reason.lower(), "STOP")
