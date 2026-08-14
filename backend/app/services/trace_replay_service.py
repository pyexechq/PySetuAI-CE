"""OTel-native stage-by-stage trace replay from audit logs (BL-074)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.trace_id import extract_trace_id
from app.models.governance import AuditLog

UAG_TRACE_MARKER = "|uag_trace="
FAILOVER_MARKER = "|failover_chain="


def _parse_json_marker(details: str, marker: str) -> Any | None:
    if marker not in details:
        return None
    payload = details.split(marker, 1)[1].strip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _usage_latency_ms(log: AuditLog, fallback: int = 200) -> int:
    usage = log.usage_metadata if isinstance(log.usage_metadata, dict) else {}
    latency = usage.get("latency_ms")
    if latency is not None:
        return max(20, int(latency))
    return max(80, fallback + (hash(str(log.id)) % 500))


def _span_status(log_status: str, allowed: bool = True) -> str:
    if not allowed or log_status == "blocked":
        return "error"
    if log_status == "review":
        return "review"
    return "ok"


def _append_span(
    spans: list[dict[str, Any]],
    *,
    name: str,
    service: str,
    duration_ms: int,
    status: str,
    stage: str,
    offset_ms: int,
    detail: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> int:
    spans.append(
        {
            "name": name,
            "service": service,
            "duration_ms": max(1, duration_ms),
            "status": status,
            "stage": stage,
            "offset_ms": offset_ms,
            "detail": detail,
            "attributes": attributes,
        }
    )
    return offset_ms + max(1, duration_ms)


def _llm_trace_spans(log: AuditLog, details: str, usage: dict[str, Any], total_ms: int) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    offset = 0
    model = str(usage.get("model") or log.resource.split("/")[0] if "/" in log.resource else log.resource)
    blocked_early = log.status == "blocked" and "egress" not in details.lower() and "Output blocked" not in details

    offset = _append_span(
        spans,
        name="gateway.receive",
        service="AI Gateway",
        duration_ms=min(25, total_ms // 12),
        status=_span_status(log.status),
        stage="ingress",
        offset_ms=offset,
        detail="OpenAI-compatible chat completion ingress",
        attributes={"actor": log.actor, "resource": log.resource},
    )

    if "PII" in details or log.action == "DLP Scan":
        offset = _append_span(
            spans,
            name="dlp.scan",
            service="DLP Service",
            duration_ms=min(35, total_ms // 10),
            status="ok",
            stage="ingress",
            offset_ms=offset,
            detail=details if "PII" in details else "Ingress content scan",
        )

    policy_status = "error" if blocked_early else _span_status(log.status)
    violation_hint = ""
    if "policy rule" in details.lower() or "violation" in details.lower():
        violation_hint = details.split(";", 1)[0]
    offset = _append_span(
        spans,
        name="policy.inspect",
        service="Policy Engine",
        duration_ms=min(45, total_ms // 8),
        status=policy_status,
        stage="ingress",
        offset_ms=offset,
        detail=violation_hint or "Ingress policy evaluation",
    )

    if blocked_early and "Prompt Injection" in log.action:
        offset = _append_span(
            spans,
            name="injection.detect",
            service="Security Scanner",
            duration_ms=min(30, total_ms // 10),
            status="error",
            stage="ingress",
            offset_ms=offset,
            detail=details,
        )

    token_saving = usage.get("token_saving")
    if isinstance(token_saving, dict) and token_saving.get("enabled"):
        offset = _append_span(
            spans,
            name="token_saving.compress",
            service="Token Saving",
            duration_ms=min(28, total_ms // 12),
            status="ok",
            stage="transform",
            offset_ms=offset,
            detail=f"Mode {token_saving.get('mode')}; saved {token_saving.get('savings_pct', 0)}%",
            attributes=token_saving,
        )

    dynamic_tools = usage.get("dynamic_tools")
    if isinstance(dynamic_tools, dict) and dynamic_tools.get("enabled"):
        offset = _append_span(
            spans,
            name="dynamic_tools.rank",
            service="MCP Broker",
            duration_ms=min(32, total_ms // 10),
            status="ok",
            stage="transform",
            offset_ms=offset,
            detail=f"Selected {dynamic_tools.get('selected_count', 0)} of {dynamic_tools.get('candidate_count', 0)} tools",
            attributes=dynamic_tools,
        )

    matched_rule = usage.get("matched_routing_rule")
    if not matched_rule and "routing_rule=" in details:
        matched_rule = details.split("routing_rule=", 1)[1].split(";", 1)[0].strip() or None
    routing_detail = f"Matched rule: {matched_rule}" if matched_rule else f"Resolved model {model}"
    if usage.get("routing_strategy") == "routing_group" and matched_rule:
        routing_detail = f"Routing group: {matched_rule}"
    offset = _append_span(
        spans,
        name="routing.select",
        service="LLM Router",
        duration_ms=min(30, total_ms // 10),
        status="ok",
        stage="routing",
        offset_ms=offset,
        detail=routing_detail,
        attributes={
            "matched_routing_rule": matched_rule,
            "routing_strategy": usage.get("routing_strategy"),
            "upstream": usage.get("upstream"),
        },
    )

    uag_trace = _parse_json_marker(details, UAG_TRACE_MARKER)
    if isinstance(uag_trace, dict):
        offset = _append_span(
            spans,
            name="uag.translate",
            service="Universal AI Gateway",
            duration_ms=int(uag_trace.get("translation_ms") or min(40, total_ms // 8)),
            status="ok",
            stage="routing",
            offset_ms=offset,
            detail=f"{uag_trace.get('source_protocol')} → {uag_trace.get('target_provider')}",
            attributes=uag_trace,
        )

    failover_chain = _parse_json_marker(details, FAILOVER_MARKER)
    llm_budget = max(60, total_ms - offset - 20)
    if isinstance(failover_chain, list) and failover_chain:
        per_failover = max(25, llm_budget // (len(failover_chain) + 1))
        for item in failover_chain:
            if not isinstance(item, dict):
                continue
            item_status = "ok" if item.get("status") == "success" else "error"
            offset = _append_span(
                spans,
                name="llm.failover",
                service=str(item.get("upstream") or "LLM Router"),
                duration_ms=per_failover,
                status=item_status,
                stage="upstream",
                offset_ms=offset,
                detail=f"{item.get('model')}: {item.get('status')}",
                attributes=item,
            )

    remaining = max(40, total_ms - offset - 15)
    llm_status = "error" if log.status == "blocked" and "Output blocked" in details else _span_status(log.status)
    offset = _append_span(
        spans,
        name="llm.complete",
        service=model,
        duration_ms=remaining,
        status=llm_status,
        stage="upstream",
        offset_ms=offset,
        detail=f"Upstream completion via {model}",
        attributes={
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
    )

    if "egress" in details.lower() or log.action == "LLM Response":
        egress_status = "error" if "Output blocked" in details else _span_status(log.status)
        offset = _append_span(
            spans,
            name="egress.inspect",
            service="Policy Engine",
            duration_ms=min(35, total_ms // 10),
            status=egress_status,
            stage="egress",
            offset_ms=offset,
            detail="Output policy + DLP scan",
        )

    _append_span(
        spans,
        name="audit.emit",
        service="Audit Log",
        duration_ms=12,
        status="ok",
        stage="audit",
        offset_ms=offset,
        detail="Persist audit + usage metadata",
        attributes={"audit_id": str(log.id)},
    )
    return spans


def _mcp_trace_spans(log: AuditLog, total_ms: int) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    offset = 0
    server = log.resource.split("/")[0] if "/" in log.resource else log.resource
    offset = _append_span(
        spans,
        name="mcp.authorize",
        service="MCP Governance",
        duration_ms=min(25, total_ms // 8),
        status=_span_status(log.status),
        stage="ingress",
        offset_ms=offset,
        detail="Tool policy + agent filter",
    )
    offset = _append_span(
        spans,
        name="mcp.invoke",
        service=server,
        duration_ms=max(40, total_ms - offset - 20),
        status=_span_status(log.status),
        stage="upstream",
        offset_ms=offset,
        detail=log.details,
    )
    _append_span(
        spans,
        name="audit.emit",
        service="Audit Log",
        duration_ms=10,
        status="ok",
        stage="audit",
        offset_ms=offset,
        detail="Tool invocation audit",
        attributes={"audit_id": str(log.id)},
    )
    return spans


def build_trace_from_audit_log(log: AuditLog) -> dict[str, Any]:
    details = log.details or ""
    usage = log.usage_metadata if isinstance(log.usage_metadata, dict) else {}
    total_ms = _usage_latency_ms(log)
    if "MCP" in log.action:
        spans = _mcp_trace_spans(log, total_ms)
    else:
        spans = _llm_trace_spans(log, details, usage, total_ms)

    trace_id = extract_trace_id(details, log.id)
    return {
        "id": str(log.id),
        "trace_id": trace_id,
        "timestamp": log.timestamp.isoformat(),
        "actor": log.actor,
        "action": log.action,
        "resource": log.resource,
        "status": log.status,
        "risk": log.risk,
        "duration_ms": total_ms,
        "span_count": len(spans),
        "spans": spans,
        "otel_trace_id": trace_id if len(trace_id) == 32 else None,
        "audit_id": str(log.id),
    }


def build_traces_from_audit_logs(logs: list[AuditLog]) -> list[dict[str, Any]]:
    return [build_trace_from_audit_log(log) for log in logs]
