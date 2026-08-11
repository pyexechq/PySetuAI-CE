from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.modules.uag.canonical import CanonicalPrompt, TranslationTrace
from app.modules.uag.provider_registry import compatibility_score, get_provider, unsupported_features
from app.modules.uag.translators import get_translator
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse


@dataclass
class ProtocolTranslator:
    source_protocol: str

    def detect_protocol(self, path: str, headers: dict[str, str] | None = None) -> str:
        lowered = path.lower()
        if "generatecontent" in lowered or headers and headers.get("x-goog-api-client"):
            return "gemini"
        if headers and headers.get("anthropic-version"):
            return "anthropic"
        return self.source_protocol

    def normalize_request(
        self,
        request: ChatCompletionRequest,
        *,
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> CanonicalPrompt:
        from app.modules.uag.canonical import build_canonical_from_openai

        return build_canonical_from_openai(
            request,
            tenant_id=tenant_id,
            metadata=metadata,
        )

    def translate_request(self, canonical: CanonicalPrompt) -> tuple[dict[str, Any], TranslationTrace]:
        started = time.perf_counter()
        translator = get_translator(canonical.target_protocol)
        payload = translator.translate_to_upstream(canonical)
        trace = TranslationTrace(
            source_protocol=canonical.source_protocol,
            requested_model=canonical.requested_model,
            canonical_model=canonical.model,
            target_provider=canonical.target_provider,
            target_protocol=canonical.target_protocol,
            translated_model=canonical.model,
            translation_ms=(time.perf_counter() - started) * 1000,
            compatibility_score=compatibility_score(canonical.source_protocol, canonical.target_provider),
            unsupported_features=unsupported_features(canonical.source_protocol, canonical.target_provider),
        )
        return payload, trace

    def translate_response(
        self,
        canonical: CanonicalPrompt,
        upstream_response: dict[str, Any] | ChatCompletionResponse,
        trace: TranslationTrace,
    ) -> ChatCompletionResponse:
        started = time.perf_counter()
        translator = get_translator(canonical.source_protocol)
        response = translator.translate_response(canonical, upstream_response)
        trace.translation_ms += (time.perf_counter() - started) * 1000
        return response


def resolve_target_protocol(provider_name: str) -> str:
    provider = get_provider(provider_name)
    return provider.protocol if provider else "openai"
