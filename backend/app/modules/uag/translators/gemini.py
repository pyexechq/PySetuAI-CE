from __future__ import annotations

from typing import Any

from app.modules.uag.canonical import CanonicalPrompt
from app.modules.uag.translators.base import OpenAICompatibleTranslator
from app.schemas.openai import ChatCompletionResponse, ChatMessage


class GeminiTranslator(OpenAICompatibleTranslator):
    protocol = "gemini"

    def translate_to_upstream(self, canonical: CanonicalPrompt) -> dict[str, Any]:
        contents = []
        system_instruction = canonical.system_prompt
        for message in canonical.messages:
            if message.role == "system":
                continue
            role = "user" if message.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": message.content}]})
        payload: dict[str, Any] = {"contents": contents}
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        payload["generationConfig"] = {
            "temperature": canonical.temperature or 0.7,
            **({"maxOutputTokens": canonical.max_tokens} if canonical.max_tokens else {}),
        }
        payload["_gemini_model"] = canonical.model
        return payload

    def translate_response(
        self,
        canonical: CanonicalPrompt,
        upstream_response: dict[str, Any] | ChatCompletionResponse,
    ) -> ChatCompletionResponse:
        if isinstance(upstream_response, ChatCompletionResponse):
            upstream_response.model = canonical.requested_model
            return upstream_response
        candidates = upstream_response.get("candidates") or []
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts") or []
            text = "".join(part.get("text", "") for part in parts)
        usage_meta = upstream_response.get("usageMetadata") or {}
        prompt_tokens = usage_meta.get("promptTokenCount", 0)
        completion_tokens = usage_meta.get("candidatesTokenCount", 0)
        return ChatCompletionResponse(
            id=f"chatcmpl-gemini-{canonical.request_id[:8]}",
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
