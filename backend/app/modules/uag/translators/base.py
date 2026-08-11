from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.modules.uag.canonical import CanonicalPrompt
from app.schemas.openai import ChatCompletionResponse, ChatMessage


class BaseTranslator(ABC):
    protocol: str = "openai"

    @abstractmethod
    def normalize_request(self, payload: dict[str, Any]) -> CanonicalPrompt:
        raise NotImplementedError

    @abstractmethod
    def translate_to_upstream(self, canonical: CanonicalPrompt) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def translate_response(
        self,
        canonical: CanonicalPrompt,
        upstream_response: dict[str, Any] | ChatCompletionResponse,
    ) -> ChatCompletionResponse:
        raise NotImplementedError


class OpenAICompatibleTranslator(BaseTranslator):
    protocol = "openai"

    def normalize_request(self, payload: dict[str, Any]) -> CanonicalPrompt:
        from app.modules.uag.canonical import build_canonical_from_openai
        from app.schemas.openai import ChatCompletionRequest

        request = ChatCompletionRequest.model_validate(payload)
        return build_canonical_from_openai(request, tenant_id="unknown")

    def translate_to_upstream(self, canonical: CanonicalPrompt) -> dict[str, Any]:
        return {
            "model": canonical.model,
            "messages": [m.model_dump() for m in canonical.messages],
            "temperature": canonical.temperature or 0.7,
            **({"max_tokens": canonical.max_tokens} if canonical.max_tokens else {}),
        }

    def translate_response(
        self,
        canonical: CanonicalPrompt,
        upstream_response: dict[str, Any] | ChatCompletionResponse,
    ) -> ChatCompletionResponse:
        if isinstance(upstream_response, ChatCompletionResponse):
            upstream_response.model = canonical.requested_model
            return upstream_response
        choice = upstream_response["choices"][0]
        usage = upstream_response.get("usage", {})
        return ChatCompletionResponse(
            id=upstream_response.get("id", "chatcmpl-uag"),
            created=upstream_response.get("created", 0),
            model=canonical.requested_model,
            choices=[
                {
                    "index": 0,
                    "message": ChatMessage(role=choice["message"]["role"], content=choice["message"]["content"]),
                    "finish_reason": choice.get("finish_reason", "stop"),
                }
            ],
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )
