"""Universal AI Gateway orchestration service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.uag.canonical import CanonicalPrompt, TranslationTrace, build_canonical_from_openai
from app.modules.uag.model_mapping import resolve_model_mapping
from app.modules.uag.protocol_translator import ProtocolTranslator, resolve_target_protocol
from app.modules.uag.translation_policy import evaluate_translation_policies
from app.modules.uag.provider_registry import get_provider
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse


@dataclass
class UagPipelineResult:
    canonical: CanonicalPrompt
    trace: TranslationTrace
    translated_request: ChatCompletionRequest


async def run_uag_pre_governance(
    db: AsyncSession,
    request: ChatCompletionRequest,
    *,
    tenant_id: uuid.UUID,
) -> UagPipelineResult:
    """Build canonical prompt and resolve target provider/model before governance."""
    translator = ProtocolTranslator(source_protocol="openai")
    canonical = translator.normalize_request(request, tenant_id=str(tenant_id))

    actual_model, target_provider, _ = await resolve_model_mapping(db, tenant_id, request.model)
    policy = await evaluate_translation_policies(db, tenant_id, canonical, target_provider)

    target_provider = policy.target_provider or target_provider
    target_protocol = resolve_target_protocol(target_provider)
    provider = get_provider(target_provider)
    if provider and provider.upstream_key != "openai" and actual_model == request.model:
        mapped_model, mapped_provider, _ = await resolve_model_mapping(db, tenant_id, request.model)
        actual_model = mapped_model
        target_provider = mapped_provider
        target_protocol = resolve_target_protocol(target_provider)

    canonical = CanonicalPrompt(
        tenant_id=str(tenant_id),
        request_id=canonical.request_id,
        source_protocol=canonical.source_protocol,
        target_provider=target_provider,
        target_protocol=target_protocol,
        model=actual_model,
        requested_model=request.model,
        messages=canonical.messages,
        tools=canonical.tools,
        system_prompt=canonical.system_prompt,
        temperature=canonical.temperature,
        max_tokens=canonical.max_tokens,
        metadata=canonical.metadata,
    )

    trace = TranslationTrace(
        source_protocol=canonical.source_protocol,
        requested_model=canonical.requested_model,
        canonical_model=canonical.model,
        target_provider=canonical.target_provider,
        target_protocol=canonical.target_protocol,
        translated_model=canonical.model,
        policy_applied=policy.policy_name,
    )

    translated_request = ChatCompletionRequest(
        model=actual_model,
        messages=request.messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=request.stream,
        routing_context=request.routing_context,
    )

    return UagPipelineResult(canonical=canonical, trace=trace, translated_request=translated_request)


async def run_uag_post_upstream(
    canonical: CanonicalPrompt,
    trace: TranslationTrace,
    response: ChatCompletionResponse,
) -> ChatCompletionResponse:
    """Translate upstream response back to the caller's source protocol."""
    translator = ProtocolTranslator(source_protocol=canonical.source_protocol)
    translated = translator.translate_response(canonical, response, trace)
    helixguard = dict(translated.helixguard or {})
    helixguard["uag"] = trace.to_dict()
    translated.helixguard = helixguard
    translated.model = canonical.requested_model
    return translated


async def simulate_translation(
    db: AsyncSession,
    request: ChatCompletionRequest,
    *,
    tenant_id: uuid.UUID,
) -> dict:
    pipeline = await run_uag_pre_governance(db, request, tenant_id=tenant_id)
    translator = ProtocolTranslator(source_protocol="openai")
    upstream_payload, trace = translator.translate_request(pipeline.canonical)
    return {
        "original_request": request.model_dump(),
        "canonical": {
            "source_protocol": pipeline.canonical.source_protocol,
            "requested_model": pipeline.canonical.requested_model,
            "model": pipeline.canonical.model,
            "target_provider": pipeline.canonical.target_provider,
            "target_protocol": pipeline.canonical.target_protocol,
            "messages": [m.model_dump() for m in pipeline.canonical.messages],
        },
        "translated_request": upstream_payload,
        "trace": trace.to_dict(),
    }
