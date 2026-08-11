from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse, ChatMessage


@dataclass
class CanonicalPrompt:
    tenant_id: str
    request_id: str
    source_protocol: str
    target_provider: str
    target_protocol: str
    model: str
    requested_model: str
    messages: list[ChatMessage]
    tools: list[dict[str, Any]] | None = None
    system_prompt: str | None = None
    temperature: float | None = 0.7
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def text_for_inspection(self) -> str:
        parts: list[str] = []
        if self.system_prompt:
            parts.append(self.system_prompt)
        for message in self.messages:
            if message.role in {"user", "system"}:
                parts.append(message.content)
        return "\n".join(parts)

    def with_model(self, model: str) -> CanonicalPrompt:
        return CanonicalPrompt(
            tenant_id=self.tenant_id,
            request_id=self.request_id,
            source_protocol=self.source_protocol,
            target_provider=self.target_provider,
            target_protocol=self.target_protocol,
            model=model,
            requested_model=self.requested_model,
            messages=list(self.messages),
            tools=self.tools,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            metadata=dict(self.metadata),
        )


@dataclass
class TranslationTrace:
    source_protocol: str
    requested_model: str
    canonical_model: str
    target_provider: str
    target_protocol: str
    translated_model: str
    governance_actions: list[str] = field(default_factory=list)
    translation_ms: float = 0.0
    policy_applied: str | None = None
    compatibility_score: float | None = None
    unsupported_features: list[str] = field(default_factory=list)
    client_response_protocol_source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_protocol": self.source_protocol,
            "requested_model": self.requested_model,
            "canonical_model": self.canonical_model,
            "target_provider": self.target_provider,
            "target_protocol": self.target_protocol,
            "translated_model": self.translated_model,
            "governance_actions": self.governance_actions,
            "translation_ms": round(self.translation_ms, 2),
            "policy_applied": self.policy_applied,
            "compatibility_score": self.compatibility_score,
            "unsupported_features": self.unsupported_features,
            "client_response_protocol_source": self.client_response_protocol_source,
        }


def build_canonical_from_openai(
    request: ChatCompletionRequest,
    *,
    tenant_id: str,
    source_protocol: str = "openai",
    target_provider: str = "openai",
    target_protocol: str = "openai",
    metadata: dict[str, Any] | None = None,
) -> CanonicalPrompt:
    system_parts = [m.content for m in request.messages if m.role == "system"]
    return CanonicalPrompt(
        tenant_id=tenant_id,
        request_id=str(uuid.uuid4()),
        source_protocol=source_protocol,
        target_provider=target_provider,
        target_protocol=target_protocol,
        model=request.model,
        requested_model=request.model,
        messages=[ChatMessage(role=m.role, content=m.content) for m in request.messages],
        system_prompt="\n".join(system_parts) if system_parts else None,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        metadata={**(metadata or {}), "routing_context": request.routing_context or {}},
    )


def apply_messages_to_request(request: ChatCompletionRequest, messages: list[ChatMessage]) -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model=request.model,
        messages=messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=request.stream,
        routing_context=request.routing_context,
    )


def attach_translation_to_response(
    response: ChatCompletionResponse,
    trace: TranslationTrace,
) -> ChatCompletionResponse:
    pysetu = dict(response.pysetu or {})
    pysetu["uag"] = trace.to_dict()
    response.pysetu = pysetu
    response.model = trace.requested_model
    return response
