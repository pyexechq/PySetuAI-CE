from __future__ import annotations

from typing import Any

from app.modules.uag.canonical import CanonicalPrompt
from app.modules.uag.translators.base import OpenAICompatibleTranslator
from app.schemas.openai import ChatCompletionResponse, ChatMessage


class ClaudeTranslator(OpenAICompatibleTranslator):
    protocol = "anthropic"

    def translate_to_upstream(self, canonical: CanonicalPrompt) -> dict[str, Any]:
        system = canonical.system_prompt
        messages = []
        for message in canonical.messages:
            if message.role == "system":
                continue
            messages.append({"role": message.role, "content": message.content})
        payload: dict[str, Any] = {
            "model": canonical.model,
            "messages": messages,
            "max_tokens": canonical.max_tokens or 1024,
            "temperature": canonical.temperature or 0.7,
        }
        if system:
            payload["system"] = system
        return payload

    def translate_response(
        self,
        canonical: CanonicalPrompt,
        upstream_response: dict[str, Any] | ChatCompletionResponse,
    ) -> ChatCompletionResponse:
        if isinstance(upstream_response, ChatCompletionResponse):
            upstream_response.model = canonical.requested_model
            return upstream_response
        content_blocks = upstream_response.get("content") or []
        text = "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")
        usage = upstream_response.get("usage") or {}
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        return ChatCompletionResponse(
            id=f"chatcmpl-claude-{canonical.request_id[:8]}",
            created=0,
            model=canonical.requested_model,
            choices=[
                {
                    "index": 0,
                    "message": ChatMessage(role="assistant", content=text),
                    "finish_reason": "stop",
                }
            ],
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        )
