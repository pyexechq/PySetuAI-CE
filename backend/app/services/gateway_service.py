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
from app.models.governance import AuditLog, MCPServer, PolicyBundle, RoutingGroup
from app.schemas.openai import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
    InspectionResult,
)
from app.modules.uag.canonical import CanonicalPrompt, TranslationTrace
from app.modules.uag.client_response import normalize_client_protocol, serialize_gateway_response
from app.modules.uag.provider_registry import get_provider
from app.modules.uag.protocol_translator import resolve_target_protocol
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
from app.services.request_log_service import (
    build_guardrail_events,
    serialize_chat_request,
    serialize_chat_response,
)
from app.services.prompt_injection_service import resolve_and_inject_prompt
from app.services.token_saving_service import apply_token_saving, resolve_token_saving_config
from app.services.dynamic_tool_service import (
    apply_dynamic_tools_for_request,
    resolve_dynamic_tool_config,
    to_openai_tools,
)
from app.services.mcp_agent_service import detect_agent, filter_servers_for_agent, toggles_from_tenant
from app.services.regional_adapters import call_bedrock_regional, call_vertex_regional
from app.services.regional_routing_service import resolve_provider_region
from app.services.http_client_pool import get_http_client
from app.services.provider_metrics_service import record_provider_request
from app.services.routing_context import build_routing_context
from app.services.secrets_service import apply_provider_gateway_credentials
from app.services.uag_admin_service import record_translation_event
from app.core.rate_limit import increment_ai_token_usage
from app.models.tenant import Tenant

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
    client_response_protocol: str = "openai"
    prompt_template_id: str | None = None
    prompt_version: int | None = None
    prompt_enforce_mode: str | None = None
    prompt_warning: str | None = None
    token_saving_enabled: bool = False
    token_saving_mode: str | None = None
    token_saving_original_tokens: int = 0
    token_saving_compressed_tokens: int = 0
    token_saving_pct: float = 0.0
    dynamic_tools_enabled: bool = False
    dynamic_tools_catalog_count: int = 0
    dynamic_tools_selected_count: int = 0
    dynamic_tools_original_tokens: int = 0
    dynamic_tools_compressed_tokens: int = 0
    dynamic_tools_pct: float = 0.0
    dynamic_tools_payload: list | None = None


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _pysetu_meta(prepared: PreparedChat, **extra) -> dict:
    meta = {
        "inspection_action": prepared.ingress.action,
        "violations": [v.model_dump() for v in prepared.ingress.violations],
        "routed_model": prepared.routed_model,
        "upstream": prepared.upstream,
    }
    if prepared.matched_routing_rule:
        meta["matched_routing_rule"] = prepared.matched_routing_rule
    if prepared.prompt_template_id:
        meta["prompt_template_id"] = prepared.prompt_template_id
        meta["prompt_version"] = prepared.prompt_version
    if prepared.prompt_warning:
        meta["prompt_warning"] = prepared.prompt_warning
    if prepared.token_saving_enabled:
        meta["token_saving"] = {
            "enabled": True,
            "mode": prepared.token_saving_mode,
            "original_tokens": prepared.token_saving_original_tokens,
            "compressed_tokens": prepared.token_saving_compressed_tokens,
            "savings_pct": prepared.token_saving_pct,
        }
    if prepared.dynamic_tools_enabled:
        meta["dynamic_tools"] = {
            "enabled": True,
            "catalog_count": prepared.dynamic_tools_catalog_count,
            "selected_count": prepared.dynamic_tools_selected_count,
            "original_tokens": prepared.dynamic_tools_original_tokens,
            "compressed_tokens": prepared.dynamic_tools_compressed_tokens,
            "savings_pct": prepared.dynamic_tools_pct,
        }
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
    prefix = "[PySetu Mock] "
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
        pysetu={
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
    *,
    usage_metadata: dict | None = None,
    request_log: dict | None = None,
) -> uuid.UUID:
    trace_id = current_trace_id()
    audit_details = f"trace_id={trace_id}; {details}" if trace_id else details
    if ctx.policy_bundle_name:
        audit_details = f"bundle={ctx.policy_bundle_name}; {audit_details}"
    if ctx.client_api_key_name:
        audit_details = f"client_key={ctx.client_api_key_name}; {audit_details}"
    log = AuditLog(
        tenant_id=ctx.tenant_id,
        timestamp=datetime.now(UTC),
        actor=ctx.actor,
        action=action,
        resource=resource,
        status=status,
        risk=risk,
        details=audit_details,
        usage_metadata=usage_metadata,
    )
    db.add(log)
    await db.flush()
    if request_log:
        from app.services.request_log_service import store_request_log_body

        await store_request_log_body(
            db,
            tenant_id=ctx.tenant_id,
            audit_log_id=log.id,
            request_payload=request_log.get("request_payload"),
            response_payload=request_log.get("response_payload"),
            guardrail_events=request_log.get("guardrail_events"),
            tool_events=request_log.get("tool_events"),
        )
    return log.id


def _token_saving_metadata(prepared: PreparedChat) -> dict | None:
    if not prepared.token_saving_enabled:
        return None
    return {
        "enabled": True,
        "mode": prepared.token_saving_mode,
        "original_tokens": prepared.token_saving_original_tokens,
        "compressed_tokens": prepared.token_saving_compressed_tokens,
        "savings_pct": prepared.token_saving_pct,
    }


def _dynamic_tools_metadata(prepared: PreparedChat) -> dict | None:
    if not prepared.dynamic_tools_enabled:
        return None
    return {
        "enabled": True,
        "catalog_count": prepared.dynamic_tools_catalog_count,
        "selected_count": prepared.dynamic_tools_selected_count,
        "original_tokens": prepared.dynamic_tools_original_tokens,
        "compressed_tokens": prepared.dynamic_tools_compressed_tokens,
        "savings_pct": prepared.dynamic_tools_pct,
    }


def _build_usage_metadata(
    ctx: GatewayContext,
    request: ChatCompletionRequest | None = None,
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: int | None = None,
    token_saving: dict | None = None,
    dynamic_tools: dict | None = None,
) -> dict:
    end_user = request.user if request and request.user else (getattr(ctx.user, "external_subject", None) if ctx.user else None)
    metadata = request.metadata if request else None
    result = {
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "auth_type": "client_key" if ctx.client_api_key_id else "jwt",
        "client_api_key_id": str(ctx.client_api_key_id) if ctx.client_api_key_id else None,
        "client_api_key_name": ctx.client_api_key_name,
        "user_id": str(ctx.user.id) if ctx.user else None,
        "end_user": end_user,
        "metadata": metadata,
        "latency_ms": latency_ms,
    }
    if token_saving:
        result["token_saving"] = token_saving
    if dynamic_tools:
        result["dynamic_tools"] = dynamic_tools
    return result


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


# Alert when a single LLM call exceeds this wall-clock latency (ms).
LATENCY_ALERT_THRESHOLD_MS = 30_000


async def _dispatch_gateway_telemetry_alert(
    db: AsyncSession,
    ctx: GatewayContext,
    *,
    action: str,
    resource: str,
    risk: str,
    details: str,
) -> None:
    """Dispatch a non-blocking operational alert (latency / outage) to tenant webhooks."""
    trace_id = current_trace_id()
    event = build_gateway_alert_event(
        action=action,
        actor=ctx.actor,
        resource=resource,
        status="review",
        risk=risk,
        details=details,
        trace_id=trace_id,
    )
    try:
        await dispatch_tenant_alerts(db, ctx.tenant_id, event)
    except Exception as exc:
        logger.warning("Gateway telemetry alert dispatch failed for tenant %s: %s", ctx.tenant_id, exc)


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
    if upstream in ("bedrock", "vertex"):
        return upstream
    return config.resolve_upstream(effective_model)


async def prepare_chat_request(
    request: ChatCompletionRequest,
    ctx: GatewayContext,
    db: AsyncSession,
    *,
    user_agent: str | None = None,
) -> tuple[PreparedChat | None, InspectionResult | None, str | None]:
    uag_pipeline = await run_uag_pre_governance(
        db,
        request,
        tenant_id=ctx.tenant_id,
        api_key_client_response_protocol=ctx.client_response_protocol,
    )
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
            sensitivity_detail = ""
            if dlp.highest_sensitivity:
                sensitivity_detail = f"; highest sensitivity: {dlp.highest_sensitivity}"
            await _write_audit(
                db,
                ctx,
                "DLP Scan",
                "gateway /ingress",
                "allowed",
                ingress.risk,
                f"PII types: {', '.join(dlp.classifications)}; {dlp.match_count} match(es) redacted{sensitivity_detail}",
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
            request_log={
                "request_payload": serialize_chat_request(request),
                "guardrail_events": build_guardrail_events(ingress=ingress),
            },
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
        return None, ingress, "Request blocked by PySetu policy engine."

    uag_trace.governance_actions.extend(["dlp", "policy_engine"])

    messages = list(effective_request.messages)
    if ingress.redacted_content:
        messages = [
            ChatMessage(role=m.role, content=ingress.redacted_content if m.role == "user" else m.content)
            if m.role == "user"
            else m
            for m in messages
        ]

    requested_template = getattr(request, "prompt_template", None) or getattr(request, "prompt_template_id", None) or getattr(request, "prompt_template_alias", None)
    req_variables = getattr(request, "variables", None)

    messages, prompt_tmpl_id, prompt_ver, prompt_enforce, prompt_warn, prompt_blocked = await resolve_and_inject_prompt(
        db, ctx.tenant_id, messages, requested_template, req_variables
    )
    if prompt_blocked:
        await _write_audit(
            db,
            ctx,
            "Policy Inspection",
            f"{effective_request.model} /chat",
            "blocked",
            "high",
            prompt_warn or "Ad-hoc system prompt blocked by tenant policy",
        )
        await db.commit()
        return None, ingress, prompt_warn or "Ad-hoc system prompts are blocked by tenant policy."

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == ctx.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    token_saving_enabled, token_saving_mode = resolve_token_saving_config(
        tenant_enabled=tenant.token_saving_enabled if tenant else False,
        tenant_mode=tenant.token_saving_mode if tenant else "both",
        request_metadata=request.metadata,
        key_enabled=ctx.token_saving_enabled,
        key_mode=ctx.token_saving_mode,
    )
    token_saving = apply_token_saving(
        messages,
        enabled=token_saving_enabled,
        mode=token_saving_mode,
    )
    messages = token_saving.messages
    if token_saving.enabled and token_saving.transformations > 0:
        uag_trace.governance_actions.append("token_saving")
    combined = "\n".join(m.content for m in messages)

    dyn_enabled, dyn_max = resolve_dynamic_tool_config(
        tenant_enabled=tenant.dynamic_tool_calling_enabled if tenant else False,
        tenant_max_tools=tenant.dynamic_tool_max if tenant else 8,
        request_metadata=request.metadata,
    )
    mcp_rows = await db.execute(select(MCPServer).where(MCPServer.tenant_id == ctx.tenant_id))
    all_mcp_servers = list(mcp_rows.scalars().all())
    from app.services.mcp_access_service import filter_servers_for_bundle

    bundle_for_mcp = await _load_bundle(db, ctx.policy_bundle_id)
    all_mcp_servers = filter_servers_for_bundle(all_mcp_servers, bundle_for_mcp)
    agent = detect_agent(user_agent, request.metadata)
    agent_toggles = toggles_from_tenant(tenant.mcp_agent_toggles if tenant else None)
    mcp_servers = filter_servers_for_agent(all_mcp_servers, agent, agent_toggles)
    if request.tools and not mcp_servers and all_mcp_servers:
        uag_trace.governance_actions.append("mcp_agent_blocked")
    dynamic_tools = apply_dynamic_tools_for_request(
        mcp_servers,
        combined,
        request.tools,
        enabled=dyn_enabled,
        max_tools=dyn_max,
        auto_hide_destructive=bool(tenant.mcp_auto_hide_destructive) if tenant else False,
    )
    dynamic_tools_payload = to_openai_tools(dynamic_tools.selected) if dynamic_tools.enabled else request.tools
    if dynamic_tools.enabled:
        uag_trace.governance_actions.append("dynamic_tools")

    routing = await select_model(
        effective_request.model,
        db,
        ctx.tenant_id,
        build_routing_context(request),
        client_api_key_id=ctx.client_api_key_id,
    )
    routed_model = routing.model
    matched_rule = routing.matched_rule
    routing_strategy = routing.strategy
    client_response_protocol = uag_pipeline.client_response_protocol
    if routing.response_format and routing.response_format.strip().lower() not in {"", "auto"}:
        client_response_protocol = normalize_client_protocol(routing.response_format)

    if routing.target_provider and canonical:
        canonical = CanonicalPrompt(
            tenant_id=canonical.tenant_id,
            request_id=canonical.request_id,
            source_protocol=client_response_protocol,
            target_provider=routing.target_provider,
            target_protocol=resolve_target_protocol(routing.target_provider),
            model=routed_model,
            requested_model=canonical.requested_model,
            messages=canonical.messages,
            tools=dynamic_tools_payload or canonical.tools,
            system_prompt=canonical.system_prompt,
            temperature=canonical.temperature,
            max_tokens=canonical.max_tokens,
            metadata=canonical.metadata,
        )
        if uag_trace:
            uag_trace.target_provider = routing.target_provider
            uag_trace.target_protocol = resolve_target_protocol(routing.target_provider)
            uag_trace.policy_applied = matched_rule or uag_trace.policy_applied

    ingress, opa_decision = await evaluate_gateway_abac(
        ctx,
        request,
        ingress,
        routed_model=routed_model,
        has_pii=dlp.has_pii,
        region=dlp.region,
        content_length=len(combined),
        entity_classifications=dlp.classifications,
        sensitivity_labels=dlp.sensitivity_labels,
        highest_sensitivity=dlp.highest_sensitivity,
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
        return None, ingress, "Request blocked by PySetu ABAC policy (OPA)."

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

    if uag_trace and canonical:
        upstream_provider = {
            "ollama": "ollama",
            "gemini": "gemini",
            "openai": "openai",
        }.get(upstream, canonical.target_provider)
        uag_trace.target_provider = upstream_provider
        uag_trace.target_protocol = resolve_target_protocol(upstream_provider)
        canonical = CanonicalPrompt(
            tenant_id=canonical.tenant_id,
            request_id=canonical.request_id,
            source_protocol=canonical.source_protocol,
            target_provider=upstream_provider,
            target_protocol=uag_trace.target_protocol,
            model=canonical.model,
            requested_model=canonical.requested_model,
            messages=canonical.messages,
            tools=dynamic_tools_payload or canonical.tools,
            system_prompt=canonical.system_prompt,
            temperature=canonical.temperature,
            max_tokens=canonical.max_tokens,
            metadata=canonical.metadata,
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
        client_response_protocol=client_response_protocol,
        prompt_template_id=prompt_tmpl_id,
        prompt_version=prompt_ver,
        prompt_enforce_mode=prompt_enforce,
        prompt_warning=prompt_warn,
        token_saving_enabled=token_saving.enabled,
        token_saving_mode=token_saving.mode if token_saving.enabled else None,
        token_saving_original_tokens=token_saving.original_tokens,
        token_saving_compressed_tokens=token_saving.compressed_tokens,
        token_saving_pct=token_saving.savings_pct,
        dynamic_tools_enabled=dynamic_tools.enabled,
        dynamic_tools_catalog_count=dynamic_tools.catalog_count,
        dynamic_tools_selected_count=dynamic_tools.selected_count,
        dynamic_tools_original_tokens=dynamic_tools.original_tokens,
        dynamic_tools_compressed_tokens=dynamic_tools.compressed_tokens,
        dynamic_tools_pct=dynamic_tools.savings_pct,
        dynamic_tools_payload=dynamic_tools_payload,
    )

    if upstream == "ollama":
        try:
            available = await list_ollama_models(config.ollama_base_url)
        except OllamaError:
            available = []
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


async def _resolve_failover_candidates(prepared: PreparedChat, db: AsyncSession, ctx: GatewayContext) -> list[str]:
    candidates = [prepared.routed_model]
    if prepared.routing_strategy == "routing_group" and prepared.matched_routing_rule:
        result = await db.execute(
            select(RoutingGroup).where(
                RoutingGroup.tenant_id == ctx.tenant_id,
                RoutingGroup.name == prepared.matched_routing_rule,
                RoutingGroup.status == "active",
            )
        )
        group = result.scalar_one_or_none()
        if group and group.members:
            sorted_members = sorted(group.members, key=lambda m: m.get("priority", 1))
            member_models = [m["model"] for m in sorted_members if isinstance(m, dict) and m.get("model")]
            for model_name in member_models:
                if model_name not in candidates:
                    candidates.append(model_name)
    return candidates


def resolve_chat_completions_url(endpoint: str) -> str:
    trimmed = endpoint.strip().rstrip("/")
    if trimmed.endswith("/chat/completions"):
        return trimmed
    if trimmed.endswith("/v1"):
        return f"{trimmed}/chat/completions"
    return f"{trimmed}/v1/chat/completions"


async def _call_openai(
    model: str,
    messages: list[ChatMessage],
    temperature: float | None,
    api_key: str,
    stream: bool = False,
    api_base: str | None = None,
    tools: list | None = None,
):
    payload = {
        "model": model,
        "messages": [m.model_dump() for m in messages],
        "temperature": temperature or 0.7,
        "stream": stream,
    }
    if tools:
        payload["tools"] = tools
    url = resolve_chat_completions_url(api_base) if api_base else "https://api.openai.com/v1/chat/completions"
    return payload, url, {"Authorization": f"Bearer {api_key}"}


async def _call_ollama_payload(
    model: str, messages: list[ChatMessage], temperature: float | None, base_url: str, stream: bool, tools: list | None = None
):
    payload = {
        "model": model,
        "messages": [m.model_dump() for m in messages],
        "temperature": temperature or 0.7,
        "stream": stream,
    }
    if tools:
        payload["tools"] = tools
    return payload, f"{base_url.rstrip('/')}/v1/chat/completions", {}


async def _execute_upstream(prepared: PreparedChat, request: ChatCompletionRequest) -> ChatCompletionResponse:
    if prepared.upstream == "openai" and prepared.config.openai_api_key:
        payload, url, headers = await _call_openai(
            prepared.routed_model,
            prepared.messages,
            request.temperature,
            prepared.config.openai_api_key,
            api_base=prepared.config.openai_api_base,
            tools=prepared.dynamic_tools_payload,
        )
        client = await get_http_client()
        response = await client.post(url, headers=headers, json=payload, timeout=120.0)
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
            pysetu=_pysetu_meta(prepared),
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
            pysetu=_pysetu_meta(prepared, gemini_model=gemini_model),
        )

    if prepared.upstream == "ollama" and prepared.ollama_model:
        payload, url, _ = await _call_ollama_payload(
            prepared.ollama_model, prepared.messages, request.temperature, prepared.config.ollama_base_url, False,
            tools=prepared.dynamic_tools_payload,
        )
        client = await get_http_client()
        response = await client.post(url, json=payload, timeout=180.0)
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
            pysetu=_pysetu_meta(prepared, ollama_model=prepared.ollama_model),
        )

    if prepared.upstream == "bedrock":
        text, bedrock_model, region = await call_bedrock_regional(
            prepared.messages,
            region=resolve_provider_region("bedrock", prepared.config.policy_bundle_name),
            model_id=prepared.routed_model,
            temperature=request.temperature,
        )
        prompt_tokens = _estimate_tokens(" ".join(m.content for m in prepared.messages))
        completion_tokens = _estimate_tokens(text)
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
            created=int(time.time()),
            model=bedrock_model,
            choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content=text))],
            usage=ChatCompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            pysetu=_pysetu_meta(prepared),
        )

    if prepared.upstream == "vertex":
        text, vertex_model, region = await call_vertex_regional(
            prepared.messages,
            region=resolve_provider_region("vertex", prepared.config.policy_bundle_name),
            model_id=prepared.routed_model,
            temperature=request.temperature,
        )
        prompt_tokens = _estimate_tokens(" ".join(m.content for m in prepared.messages))
        completion_tokens = _estimate_tokens(text)
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
            created=int(time.time()),
            model=vertex_model,
            choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content=text))],
            usage=ChatCompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            pysetu=_pysetu_meta(prepared),
        )

    mock = _build_mock_response(prepared.routed_model, prepared.combined, prepared.ingress)
    mock.pysetu = _pysetu_meta(prepared)
    mock.pysetu["routed_model"] = prepared.routed_model
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
                api_base=prepared.config.openai_api_base,
                tools=prepared.dynamic_tools_payload,
            )
            client = await get_http_client()
            async with client.stream("POST", url, headers=headers, json=payload, timeout=180.0) as response:
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
                prepared.ollama_model, prepared.messages, request.temperature, prepared.config.ollama_base_url, True,
                tools=prepared.dynamic_tools_payload,
            )
            client = await get_http_client()
            async with client.stream("POST", url, json=payload, timeout=180.0) as response:
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
        if latency_ms >= LATENCY_ALERT_THRESHOLD_MS:
            await _dispatch_gateway_telemetry_alert(
                db,
                ctx,
                action="gateway.latency.high",
                resource=f"{prepared.routed_model} /chat",
                risk="medium",
                details=f"LLM latency {latency_ms}ms exceeded {LATENCY_ALERT_THRESHOLD_MS}ms threshold (streamed)",
            )
        prompt_tokens = _estimate_tokens(prepared.combined)
        full_text_str = "".join(full_text)
        completion_tokens = _estimate_tokens(full_text_str)
        total_tokens = prompt_tokens + completion_tokens
        await record_provider_request(db, ctx.tenant_id, prepared.routed_model, latency_ms, success=True)
        
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == ctx.tenant_id))
        tenant = tenant_result.scalar_one()

        if ctx.client_api_key_id:
            increment_ai_token_usage(
                f"{ctx.tenant_id}:key:{ctx.client_api_key_id}",
                ctx.ai_token_limit_tpm,
                ctx.ai_token_limit_tph,
                ctx.ai_token_limit_tpd,
                total_tokens,
            )

        increment_ai_token_usage(
            str(ctx.tenant_id),
            tenant.ai_token_limit_tpm,
            tenant.ai_token_limit_tph,
            tenant.ai_token_limit_tpd,
            total_tokens,
        )

        region = infer_region_from_bundle(ctx.policy_bundle_name)
        dlp = dlp_scan_content(full_text_str, region=region)
        inspect_content_text = dlp.redacted_content or full_text_str
        inspect_context = {"has_pii": dlp.has_pii, "region": dlp.region}
        bundle = await _load_bundle(db, ctx.policy_bundle_id)
        egress = await inspect_for_gateway(db, ctx.tenant_id, bundle, inspect_content_text, context=inspect_context)

        if prepared.uag_trace:
            prepared.uag_trace.governance_actions.append("egress_policy")

        audit_status = "allowed"
        audit_risk = egress.risk if egress.risk != "low" else prepared.ingress.risk
        if not egress.allowed:
            audit_status = "blocked"
            await _dispatch_gateway_block_alert(
                db,
                ctx,
                audit_action="LLM Response",
                resource=f"{prepared.routed_model} /chat",
                risk=egress.risk,
                details="Output blocked by egress policy (streamed)",
            )
        elif egress.violations or dlp.has_pii:
            audit_status = "review"

        if egress.violations:
            audit_details += f"; {len(egress.violations)} egress rule violation(s)"
        if dlp.has_pii:
            audit_details += f"; PII detected in output ({', '.join(dlp.classifications)})"

        await _write_audit(
            db, 
            ctx, 
            "LLM Response" if not egress.allowed else "LLM Request", 
            f"{prepared.routed_model} /chat", 
            audit_status, 
            audit_risk, 
            audit_details,
            usage_metadata=_build_usage_metadata(
                ctx,
                request=request,
                model=prepared.routed_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=latency_ms,
                token_saving=_token_saving_metadata(prepared),
                dynamic_tools=_dynamic_tools_metadata(prepared),
            ),
            request_log={
                "request_payload": serialize_chat_request(request),
                "response_payload": {
                    "model": prepared.routed_model,
                    "content": inspect_content_text,
                    "stream": True,
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    },
                },
                "guardrail_events": build_guardrail_events(ingress=prepared.ingress, egress=egress),
            },
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
        await _dispatch_gateway_telemetry_alert(
            db,
            ctx,
            action="gateway.upstream.outage",
            resource=f"{prepared.routed_model} /chat",
            risk="high",
            details=f"Upstream provider error during streaming: {exc}",
        )


async def process_chat_completion(
    request: ChatCompletionRequest,
    ctx: GatewayContext,
    db: AsyncSession,
    *,
    user_agent: str | None = None,
) -> tuple[dict | None, InspectionResult | None, str | None]:
    with tracer.start_as_current_span("gateway.chat_completion") as span:
        span.set_attribute("pysetu.model", request.model)
        span.set_attribute("pysetu.stream", bool(request.stream))
        prepared, ingress, error = await prepare_chat_request(request, ctx, db, user_agent=user_agent)
        if error or prepared is None:
            span.set_attribute("pysetu.result", "blocked" if ingress and not ingress.allowed else "error")
            return None, ingress, error

        span.set_attribute("pysetu.upstream", prepared.upstream)
        started = time.perf_counter()
        candidates = await _resolve_failover_candidates(prepared, db, ctx)
        failover_chain: list[dict] = []
        response = None
        last_exception = None

        for candidate_model in candidates:
            prepared.routed_model = candidate_model
            prepared.upstream = coerce_upstream(
                prepared.config.resolve_upstream(candidate_model),
                prepared.config,
                candidate_model,
                candidate_model,
            )
            if prepared.upstream == "ollama":
                try:
                    available = await list_ollama_models(prepared.config.ollama_base_url)
                except OllamaError:
                    available = []
                prepared.ollama_model = resolve_ollama_model(candidate_model, available, prepared.config.ollama_default_model)
                prepared.gemini_model = None
            elif prepared.upstream == "gemini":
                prepared.gemini_model = normalize_gemini_model(candidate_model, prepared.config.gemini_default_model)
                prepared.ollama_model = None
            else:
                prepared.ollama_model = None
                prepared.gemini_model = None

            sub_started = time.perf_counter()
            try:
                response = await _execute_upstream(prepared, request)
                if failover_chain:
                    failover_chain.append({"model": candidate_model, "upstream": prepared.upstream, "status": "success"})
                break
            except (httpx.HTTPError, GeminiError, OllamaError) as exc:
                last_exception = exc
                sub_latency = max(1, int((time.perf_counter() - sub_started) * 1000))
                await record_provider_request(db, ctx.tenant_id, candidate_model, sub_latency, success=False)
                failover_chain.append({
                    "model": candidate_model,
                    "upstream": prepared.upstream,
                    "status": "failed",
                    "error": str(exc),
                })
                logger.warning("Upstream failure for %s via %s: %s", candidate_model, prepared.upstream, exc)

        if response is None:
            span.record_exception(last_exception)
            latency_ms = max(1, int((time.perf_counter() - started) * 1000))
            failover_summary = "; ".join(f"{item['model']}({item['upstream']}): {item['error']}" for item in failover_chain)
            audit_msg = f"All provider targets failed: {failover_summary}"
            await _write_audit(db, ctx, "LLM Request", f"{prepared.routed_model} /chat", "review", "medium", audit_msg)
            await db.commit()
            await _dispatch_gateway_telemetry_alert(
                db,
                ctx,
                action="gateway.upstream.outage",
                resource=f"{prepared.routed_model} /chat",
                risk="high",
                details=f"All provider targets failed: {failover_summary}",
            )
            return None, prepared.ingress, f"Upstream provider error: {last_exception}"

        latency_ms = max(1, int((time.perf_counter() - started) * 1000))

        if latency_ms >= LATENCY_ALERT_THRESHOLD_MS:
            await _dispatch_gateway_telemetry_alert(
                db,
                ctx,
                action="gateway.latency.high",
                resource=f"{prepared.routed_model} /chat",
                risk="medium",
                details=f"LLM latency {latency_ms}ms exceeded {LATENCY_ALERT_THRESHOLD_MS}ms threshold",
            )

        region = infer_region_from_bundle(ctx.policy_bundle_name)
        raw_response_text = response.choices[0].message.content
        dlp = dlp_scan_content(raw_response_text, region=region)
        inspect_content_text = dlp.redacted_content or raw_response_text
        inspect_context = {"has_pii": dlp.has_pii, "region": dlp.region}

        bundle = await _load_bundle(db, ctx.policy_bundle_id)
        egress = await inspect_for_gateway(db, ctx.tenant_id, bundle, inspect_content_text, context=inspect_context)
        if not egress.allowed:
            span.set_attribute("pysetu.result", "egress_blocked")
            await _write_audit(
                db,
                ctx,
                "LLM Response",
                f"{prepared.routed_model} /chat",
                "blocked",
                egress.risk,
                "Output blocked by egress policy",
                request_log={
                    "request_payload": serialize_chat_request(request),
                    "response_payload": serialize_chat_response(response),
                    "guardrail_events": build_guardrail_events(ingress=prepared.ingress, egress=egress),
                },
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
            return None, egress, "Response blocked by PySetu egress inspection."

        # Apply output redaction if DLP or egress rules redacted text
        effective_redacted = egress.redacted_content or dlp.redacted_content
        if effective_redacted and response.choices and len(response.choices) > 0:
            response.choices[0].message.content = effective_redacted

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
        if failover_chain:
            audit_details += f" |failover_chain={json.dumps(failover_chain, separators=(',', ':'))}"
            response.pysetu["failover_chain"] = failover_chain

        tenant_result = await db.execute(select(Tenant).where(Tenant.id == ctx.tenant_id))
        tenant = tenant_result.scalar_one()

        if ctx.client_api_key_id:
            increment_ai_token_usage(
                f"{ctx.tenant_id}:key:{ctx.client_api_key_id}",
                ctx.ai_token_limit_tpm,
                ctx.ai_token_limit_tph,
                ctx.ai_token_limit_tpd,
                response.usage.total_tokens,
            )

        increment_ai_token_usage(
            str(ctx.tenant_id),
            tenant.ai_token_limit_tpm,
            tenant.ai_token_limit_tph,
            tenant.ai_token_limit_tpd,
            response.usage.total_tokens,
        )

        await _write_audit(
            db,
            ctx,
            "LLM Request",
            f"{prepared.routed_model} /chat",
            audit_status,
            prepared.ingress.risk,
            audit_details,
            usage_metadata=_build_usage_metadata(
                ctx,
                request=request,
                model=prepared.routed_model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                latency_ms=latency_ms,
                token_saving=_token_saving_metadata(prepared),
                dynamic_tools=_dynamic_tools_metadata(prepared),
            ),
            request_log={
                "request_payload": serialize_chat_request(request),
                "response_payload": serialize_chat_response(response),
                "guardrail_events": build_guardrail_events(ingress=prepared.ingress, egress=egress),
            },
        )
        await db.commit()
        span.set_attribute("pysetu.result", audit_status)
        return serialize_gateway_response(
            prepared.client_response_protocol,
            response,
            prepared.uag_canonical,
            prepared.uag_trace,
            include_metadata=ctx.debug_mode,
        ), prepared.ingress, None
