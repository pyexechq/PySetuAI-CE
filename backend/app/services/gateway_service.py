import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.telemetry import current_trace_id, get_tracer
from app.models.governance import AuditLog, PolicyBundle
from app.schemas.openai import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
    InspectionResult,
)
from app.modules.uag.canonical import CanonicalPrompt, TranslationTrace
from app.modules.uag.provider_registry import get_provider
from app.modules.uag.service import run_uag_post_upstream, run_uag_pre_governance
from app.services.alert_webhook_service import (
    build_gateway_alert_event,
    dispatch_tenant_alerts,
    gateway_block_action,
)
from app.services.dlp_service import infer_region_from_bundle
from app.services.dlp_service import scan_content as dlp_scan_content
from app.services.gateway_context import GatewayContext
from app.services.gemini_client import GeminiError, call_gemini, normalize_gemini_model, stream_gemini
from app.services.injection_detection_service import is_injection_related_violation
from app.services.integration_service import GatewayConfig, resolve_gateway_config
from app.services.llm_router import select_model
from app.services.ollama_client import OllamaError, list_ollama_models, resolve_ollama_model
from app.services.opa_service import evaluate_gateway_abac
from app.services.policy_engine import inspect_for_gateway
from app.services.provider_metrics_service import record_provider_request
from app.services.routing_context import build_routing_context
from app.services.secrets_service import apply_provider_gateway_credentials
from app.services.uag_admin_service import record_translation_event

tracer = get_tracer(__name__)
logger = logging.getLogger(__name__)


@dataclass
class PreparedChat:
    messages: list[ChatMessage]
    routed_model: str
    upstream: str
    config: GatewayConfig
    ingress: InspectionResult
    combined: str
    matched_routing_rule: str | None = None
    routing_strategy: str = "passthrough"
    ollama_model: str | None = None
    gemini_model: str | None = None
    policy_bundle_id: str | None = None
    policy_bundle_name: str | None = None
    client_api_key_name: str | None = None
    opa_applied: bool = False
    opa_skipped: bool = False
    uag_canonical: CanonicalPrompt | None = None
    uag_trace: TranslationTrace | None = None
    requested_model: str | None = None


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _helixguard_meta(prepared: PreparedChat, **extra) -> dict:
    meta = {
        "inspection_action": prepared.ingress.action,
        "violations": [v.model_dump() for v in prepared.ingress.violations],
        "routed_model": prepared.routed_model,
        "upstream": prepared.upstream,
    }
    if prepared.matched_routing_rule:
        meta["matched_routing_rule"] = prepared.matched_routing_rule
    if prepared.policy_bundle_name:
        meta["policy_bundle"] = prepared.policy_bundle_name
    if prepared.client_api_key_name:
        meta["client_api_key"] = prepared.client_api_key_name
    if prepared.routing_strategy:
        meta["routing_strategy"] = prepared.routing_strategy
    if prepared.opa_applied:
        meta["abac_engine"] = "opa"
    if prepared.opa_skipped:
        meta["opa_skipped"] = True
    if prepared.uag_trace:
        meta["uag"] = prepared.uag_trace.to_dict()
    meta.update(extra)
    return meta


def _build_mock_response(model: str, prompt: str, inspection: InspectionResult) -> ChatCompletionResponse:
    prefix = "[HelixGuard Mock] "
    if inspection.action == "redact":
        prefix += "Content was redacted before processing. "
    reply = (
        f"{prefix}Processed by {model}. "
        f"Simulated response — configure OPENAI_API_KEY, GEMINI_API_KEY, or Ollama for live inference."
    )
    prompt_tokens = _estimate_tokens(prompt)
    completion_tokens = _estimate_tokens(reply)
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        created=int(time.time()),
        model=model,
        choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content=reply))],
        usage=ChatCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
        helixguard={
            "inspection_action": inspection.action,
            "violations": [v.model_dump() for v in inspection.violations],
            "upstream": "mock",
        },
    )


async def _write_audit(
    db: AsyncSession,
    ctx: GatewayContext,
    action: str,
    resource: str,
    status: str,
    risk: str,
    details: str,
) -> None:
    trace_id = current_trace_id()
    audit_details = f"trace_id={trace_id}; {details}" if trace_id else details
    if ctx.policy_bundle_name:
        audit_details = f"bundle={ctx.policy_bundle_name}; {audit_details}"
    if ctx.client_api_key_name:
        audit_details = f"client_key={ctx.client_api_key_name}; {audit_details}"
    db.add(
        AuditLog(
            tenant_id=ctx.tenant_id,
            timestamp=datetime.now(UTC),
            actor=ctx.actor,
            action=action,
            resource=resource,
            status=status,
            risk=risk,
            details=audit_details,
        )
    )


async def _dispatch_gateway_block_alert(
    db: AsyncSession,
    ctx: GatewayContext,
    *,
    audit_action: str,
    resource: str,
    risk: str,
    details: str,
    injection: bool = False,
) -> None:
    trace_id = current_trace_id()
    event = build_gateway_alert_event(
        action=gateway_block_action(audit_action, injection=injection),
        actor=ctx.actor,
        resource=resource,
        status="blocked",
        risk=risk,
        details=details,
        trace_id=trace_id,
    )
    try:
        await dispatch_tenant_alerts(db, ctx.tenant_id, event)
    except Exception as exc:
        logger.warning("Gateway alert dispatch failed for tenant %s: %s", ctx.tenant_id, exc)


async def _load_bundle(db: AsyncSession, bundle_id) -> PolicyBundle | None:
    if not bundle_id:
        return None
    result = await db.execute(select(PolicyBundle).where(PolicyBundle.id == bundle_id))
    return result.scalar_one_or_none()


def coerce_upstream(
    upstream: str,
    config: GatewayConfig,
    model: str,
    routed_model: str,
) -> str:
    """Use the requested upstream only when credentials are available; otherwise fall back."""
    effective_model = model if model != "auto" else routed_model
    if upstream == "openai" and config.openai_api_key:
        return "openai"
    if upstream == "gemini" and config.gemini_api_key:
        return "gemini"
    if upstream == "ollama" and config.ollama_enabled:
        return "ollama"
    return config.resolve_upstream(effective_model)


async def prepare_chat_request(
    request: ChatCompletionRequest,
    ctx: GatewayContext,
    db: AsyncSession,
) -> tuple[PreparedChat | None, InspectionResult | None, str | None]:
    uag_pipeline = await run_uag_pre_governance(db, request, tenant_id=ctx.tenant_id)
    canonical = uag_pipeline.canonical
    uag_trace = uag_pipeline.trace
    effective_request = uag_pipeline.translated_request

    combined = canonical.text_for_inspection()
    bundle = await _load_bundle(db, ctx.policy_bundle_id)
    region = infer_region_from_bundle(ctx.policy_bundle_name)
    dlp = dlp_scan_content(combined, region=region)
    inspect_content = dlp.redacted_content or combined
    inspect_context = {"has_pii": dlp.has_pii, "region": dlp.region}
    ingress = await inspect_for_gateway(
        db,
        ctx.tenant_id,
        bundle,
        inspect_content,
        context=inspect_context,
    )

    if dlp.redacted_content and ingress.allowed and ingress.action != "block":
        if ingress.redacted_content:
            merged = ingress.redacted_content
        else:
            merged = dlp.redacted_content
            ingress = InspectionResult(
                allowed=True,
                action="redact",
                violations=ingress.violations,
                redacted_content=merged,
                risk=ingress.risk if ingress.risk != "low" else "medium",
            )
        if dlp.classifications:
            await _write_audit(
                db,
                ctx,
                "DLP Scan",
                "gateway /ingress",
                "allowed",
                ingress.risk,
                f"PII types: {', '.join(dlp.classifications)}; {dlp.match_count} match(es) redacted",
            )

    if not ingress.allowed:
        violation_names = [v.rule_name for v in ingress.violations]
        detail_text = "; ".join(v.detail for v in ingress.violations) or "Policy violation"
        audit_action = (
            "Prompt Injection" if is_injection_related_violation(violation_names, detail_text) else "LLM Request"
        )
        await _write_audit(
            db,
            ctx,
            audit_action,
            f"{request.model} /chat",
            "blocked",
            ingress.risk,
            detail_text,
        )
        await db.commit()
        await _dispatch_gateway_block_alert(
            db,
            ctx,
            audit_action=audit_action,
            resource=f"{request.model} /chat",
            risk=ingress.risk,
            details=detail_text,
            injection=is_injection_related_violation(violation_names, detail_text),
        )
        return None, ingress, "Request blocked by HelixGuard policy engine."

    uag_trace.governance_actions.extend(["dlp", "policy_engine"])

    messages = list(effective_request.messages)
    if ingress.redacted_content:
        messages = [
            ChatMessage(role=m.role, content=ingress.redacted_content if m.role == "user" else m.content)
            if m.role == "user"
            else m
            for m in messages
        ]

    routed_model, matched_rule, routing_strategy = await select_model(
        effective_request.model,
        db,
        ctx.tenant_id,
        build_routing_context(request),
    )

    ingress, opa_decision = await evaluate_gateway_abac(
        ctx,
        request,
        ingress,
        routed_model=routed_model,
        has_pii=dlp.has_pii,
        region=dlp.region,
        content_length=len(combined),
    )
    if not ingress.allowed:
        violation_names = [v.rule_name for v in ingress.violations]
        detail_text = "; ".join(v.detail for v in ingress.violations) or "ABAC policy violation"
        await _write_audit(
            db,
            ctx,
            "ABAC Policy",
            f"{routed_model} /chat",
            "blocked",
            ingress.risk,
            detail_text,
        )
        await db.commit()
        await _dispatch_gateway_block_alert(
            db,
            ctx,
            audit_action="ABAC Policy",
            resource=f"{routed_model} /chat",
            risk=ingress.risk,
            details=detail_text,
        )
        return None, ingress, "Request blocked by HelixGuard ABAC policy (OPA)."

    uag_trace.governance_actions.append("opa")

    config = await resolve_gateway_config(db, ctx.tenant_id)
    config = await apply_provider_gateway_credentials(db, ctx.tenant_id, routed_model, config)
    provider_def = get_provider(canonical.target_provider)
    if provider_def:
        upstream = provider_def.upstream_key
    else:
        upstream = config.resolve_upstream(effective_request.model if effective_request.model != "auto" else routed_model)
    upstream = coerce_upstream(
        upstream,
        config,
        effective_request.model,
        routed_model,
    )

    prepared = PreparedChat(
        messages=messages,
        routed_model=routed_model,
        upstream=upstream,
        config=config,
        ingress=ingress,
        combined=combined,
        matched_routing_rule=matched_rule,
        routing_strategy=routing_strategy,
        policy_bundle_id=str(ctx.policy_bundle_id) if ctx.policy_bundle_id else None,
        policy_bundle_name=ctx.policy_bundle_name,
        client_api_key_name=ctx.client_api_key_name,
        opa_applied=opa_decision.available and not opa_decision.skipped,
        opa_skipped=opa_decision.skipped,
        uag_canonical=canonical,
        uag_trace=uag_trace,
        requested_model=request.model,
    )

    if upstream == "ollama":
        available = await list_ollama_models(config.ollama_base_url)
        prepared.ollama_model = resolve_ollama_model(
            effective_request.model if effective_request.model != "auto" else routed_model,
            available,
            config.ollama_default_model,
        )
    elif upstream == "gemini":
        prepared.gemini_model = normalize_gemini_model(
            effective_request.model if "gemini" in effective_request.model.lower() else routed_model,
            config.gemini_default_model,
        )

    return prepared, ingress, None


async def _call_openai(
    model: str, messages: list[ChatMessage], temperature: float | None, api_key: str, stream: bool = False
):
    payload = {
        "model": model,
        "messages": [m.model_dump() for m in messages],
        "temperature": temperature or 0.7,
        "stream": stream,
    }
    return payload, "https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {api_key}"}


async def _call_ollama_payload(
    model: str, messages: list[ChatMessage], temperature: float | None, base_url: str, stream: bool
):
    payload = {
        "model": model,
        "messages": [m.model_dump() for m in messages],
        "temperature": temperature or 0.7,
        "stream": stream,
    }
    return payload, f"{base_url.rstrip('/')}/v1/chat/completions", {}


async def _execute_upstream(prepared: PreparedChat, request: ChatCompletionRequest) -> ChatCompletionResponse:
    if prepared.upstream == "openai" and prepared.config.openai_api_key:
        payload, url, headers = await _call_openai(
            prepared.routed_model, prepared.messages, request.temperature, prepared.config.openai_api_key
        )
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return ChatCompletionResponse(
            id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:24]}"),
            created=data.get("created", int(time.time())),
            model=data.get("model", prepared.routed_model),
            choices=[
                ChatCompletionChoice(
                    message=ChatMessage(role=choice["message"]["role"], content=choice["message"]["content"]),
                    finish_reason=choice.get("finish_reason", "stop"),
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            ),
            helixguard=_helixguard_meta(prepared),
        )

    if prepared.upstream == "gemini" and prepared.config.gemini_api_key and prepared.gemini_model:
        text, gemini_model = await call_gemini(
            prepared.gemini_model,
            prepared.messages,
            prepared.config.gemini_api_key,
            request.temperature,
        )
        prompt_tokens = _estimate_tokens(" ".join(m.content for m in prepared.messages))
        completion_tokens = _estimate_tokens(text)
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
            created=int(time.time()),
            model=gemini_model,
            choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content=text))],
            usage=ChatCompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            helixguard=_helixguard_meta(prepared, gemini_model=gemini_model),
        )

    if prepared.upstream == "ollama" and prepared.ollama_model:
        payload, url, _ = await _call_ollama_payload(
            prepared.ollama_model, prepared.messages, request.temperature, prepared.config.ollama_base_url, False
        )
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return ChatCompletionResponse(
            id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:24]}"),
            created=data.get("created", int(time.time())),
            model=data.get("model", prepared.ollama_model),
            choices=[
                ChatCompletionChoice(
                    message=ChatMessage(role=choice["message"]["role"], content=choice["message"]["content"]),
                    finish_reason=choice.get("finish_reason", "stop"),
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=usage.get("prompt_tokens", _estimate_tokens(prepared.combined)),
                completion_tokens=usage.get("completion_tokens", _estimate_tokens(choice["message"]["content"])),
                total_tokens=usage.get("total_tokens", 0),
            ),
            helixguard=_helixguard_meta(prepared, ollama_model=prepared.ollama_model),
        )

    mock = _build_mock_response(prepared.routed_model, prepared.combined, prepared.ingress)
    mock.helixguard = _helixguard_meta(prepared)
    mock.helixguard["routed_model"] = prepared.routed_model
    return mock


def _chunk_payload(
    completion_id: str, model: str, content: str | None, role: str | None = None, finish: bool = False
) -> str:
    delta: dict = {}
    if role:
        delta["role"] = role
    if content is not None:
        delta["content"] = content
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": "stop" if finish else None,
            }
        ],
    }
    return f"data: {json.dumps(payload)}\n\n"


async def stream_chat_completion(
    prepared: PreparedChat,
    request: ChatCompletionRequest,
    ctx: GatewayContext,
    db: AsyncSession,
) -> AsyncIterator[str]:
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    model_name = prepared.gemini_model or prepared.ollama_model or prepared.routed_model
    full_text: list[str] = []
    started = time.perf_counter()

    yield _chunk_payload(completion_id, model_name, None, role="assistant")

    try:
        if prepared.upstream == "openai" and prepared.config.openai_api_key:
            payload, url, headers = await _call_openai(
                prepared.routed_model,
                prepared.messages,
                request.temperature,
                prepared.config.openai_api_key,
                stream=True,
            )
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        event = json.loads(raw)
                        delta = event.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            full_text.append(content)
                            yield _chunk_payload(completion_id, model_name, content)

        elif prepared.upstream == "gemini" and prepared.config.gemini_api_key and prepared.gemini_model:
            async for delta in stream_gemini(
                prepared.gemini_model,
                prepared.messages,
                prepared.config.gemini_api_key,
                request.temperature,
            ):
                full_text.append(delta)
                yield _chunk_payload(completion_id, prepared.gemini_model, delta)

        elif prepared.upstream == "ollama" and prepared.ollama_model:
            payload, url, _ = await _call_ollama_payload(
                prepared.ollama_model, prepared.messages, request.temperature, prepared.config.ollama_base_url, True
            )
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        event = json.loads(raw)
                        delta = event.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            full_text.append(content)
                            yield _chunk_payload(completion_id, prepared.ollama_model, content)

        else:
            mock_text = (
                _build_mock_response(prepared.routed_model, prepared.combined, prepared.ingress)
                .choices[0]
                .message.content
            )
            for word in mock_text.split(" "):
                token = word + " "
                full_text.append(token)
                yield _chunk_payload(completion_id, model_name, token)

        yield _chunk_payload(completion_id, model_name, None, finish=True)
        yield "data: [DONE]\n\n"

        audit_details = f"Streamed to {model_name} via {prepared.upstream}"
        latency_ms = max(1, int((time.perf_counter() - started) * 1000))
        await record_provider_request(db, ctx.tenant_id, prepared.routed_model, latency_ms, success=True)
        await _write_audit(
            db, ctx, "LLM Request", f"{prepared.routed_model} /chat", "allowed", prepared.ingress.risk, audit_details
        )
        await db.commit()

    except (httpx.HTTPError, GeminiError, OllamaError) as exc:
        error_payload = {"error": {"message": str(exc), "type": "upstream_error", "code": "stream_failed"}}
        yield f"data: {json.dumps(error_payload)}\n\n"
        yield "data: [DONE]\n\n"
        latency_ms = max(1, int((time.perf_counter() - started) * 1000))
        await record_provider_request(db, ctx.tenant_id, prepared.routed_model, latency_ms, success=False)
        await _write_audit(db, ctx, "LLM Request", f"{prepared.routed_model} /chat", "review", "medium", str(exc))
        await db.commit()


async def process_chat_completion(
    request: ChatCompletionRequest,
    ctx: GatewayContext,
    db: AsyncSession,
) -> tuple[ChatCompletionResponse | None, InspectionResult | None, str | None]:
    with tracer.start_as_current_span("gateway.chat_completion") as span:
        span.set_attribute("helixguard.model", request.model)
        span.set_attribute("helixguard.stream", bool(request.stream))
        prepared, ingress, error = await prepare_chat_request(request, ctx, db)
        if error or prepared is None:
            span.set_attribute("helixguard.result", "blocked" if ingress and not ingress.allowed else "error")
            return None, ingress, error

        span.set_attribute("helixguard.upstream", prepared.upstream)
        started = time.perf_counter()
        try:
            response = await _execute_upstream(prepared, request)
        except (httpx.HTTPError, GeminiError, OllamaError) as exc:
            span.record_exception(exc)
            latency_ms = max(1, int((time.perf_counter() - started) * 1000))
            await record_provider_request(db, ctx.tenant_id, prepared.routed_model, latency_ms, success=False)
            await _write_audit(db, ctx, "LLM Request", f"{prepared.routed_model} /chat", "review", "medium", str(exc))
            await db.commit()
            return None, prepared.ingress, f"Upstream provider error: {exc}"

        latency_ms = max(1, int((time.perf_counter() - started) * 1000))

        bundle = await _load_bundle(db, ctx.policy_bundle_id)
        egress = await inspect_for_gateway(db, ctx.tenant_id, bundle, response.choices[0].message.content)
        if not egress.allowed:
            span.set_attribute("helixguard.result", "egress_blocked")
            await _write_audit(
                db,
                ctx,
                "LLM Response",
                f"{prepared.routed_model} /chat",
                "blocked",
                egress.risk,
                "Output blocked by egress policy",
            )
            await db.commit()
            await _dispatch_gateway_block_alert(
                db,
                ctx,
                audit_action="LLM Response",
                resource=f"{prepared.routed_model} /chat",
                risk=egress.risk,
                details="Output blocked by egress policy",
            )
            return None, egress, "Response blocked by HelixGuard egress inspection."

        await record_provider_request(db, ctx.tenant_id, prepared.routed_model, latency_ms, success=True)

        if prepared.uag_canonical and prepared.uag_trace:
            response = await run_uag_post_upstream(prepared.uag_canonical, prepared.uag_trace, response)
            prepared.uag_trace.governance_actions.append("egress_policy")
            await record_translation_event(
                db,
                tenant_id=ctx.tenant_id,
                request_id=prepared.uag_canonical.request_id,
                source_protocol=prepared.uag_trace.source_protocol,
                target_provider=prepared.uag_trace.target_provider,
                requested_model=prepared.uag_trace.requested_model,
                translated_model=prepared.uag_trace.translated_model,
                success=True,
                latency_ms=prepared.uag_trace.translation_ms,
                compatibility_score=prepared.uag_trace.compatibility_score,
                details="; ".join(prepared.uag_trace.governance_actions),
            )

        audit_status = "review" if prepared.ingress.violations else "allowed"
        audit_details = f"Routed to {prepared.routed_model} via {prepared.upstream}"
        if prepared.requested_model and prepared.requested_model != prepared.routed_model:
            audit_details = (
                f"UAG translated {prepared.requested_model} → {prepared.routed_model} via {prepared.upstream}"
            )
        if prepared.ollama_model:
            audit_details += f" (Ollama: {prepared.ollama_model})"
        if prepared.gemini_model:
            audit_details += f" (Gemini: {prepared.gemini_model})"
        if prepared.ingress.violations:
            audit_details += f"; {len(prepared.ingress.violations)} policy rule(s) applied"
        if prepared.uag_trace:
            audit_details += f" |uag_trace={json.dumps(prepared.uag_trace.to_dict(), separators=(',', ':'))}"

        await _write_audit(
            db,
            ctx,
            "LLM Request",
            f"{prepared.routed_model} /chat",
            audit_status,
            prepared.ingress.risk,
            audit_details,
        )
        await db.commit()
        span.set_attribute("helixguard.result", audit_status)
        return response, prepared.ingress, None
