"""Tests for OTel trace replay (BL-074)."""

import uuid
from datetime import UTC, datetime

from app.models.governance import AuditLog
from app.services.trace_replay_service import build_trace_from_audit_log


def _log(**kwargs) -> AuditLog:
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "timestamp": datetime.now(UTC),
        "actor": "admin@acme.com",
        "action": "LLM Request",
        "resource": "gpt-4o /chat",
        "status": "allowed",
        "risk": "low",
        "details": "trace_id=abc123def45678901234567890123456; Routed to gpt-4o via openai",
        "usage_metadata": {
            "model": "gpt-4o",
            "latency_ms": 420,
            "prompt_tokens": 50,
            "completion_tokens": 30,
            "total_tokens": 80,
            "token_saving": {"enabled": True, "mode": "both", "savings_pct": 12},
        },
    }
    defaults.update(kwargs)
    return AuditLog(**defaults)


def test_build_trace_includes_gateway_stages() -> None:
    trace = build_trace_from_audit_log(_log())
    assert trace["trace_id"] == "abc123def45678901234567890123456"
    assert trace["span_count"] >= 5
    names = [span["name"] for span in trace["spans"]]
    assert "gateway.receive" in names
    assert "policy.inspect" in names
    assert "llm.complete" in names
    assert "audit.emit" in names


def test_build_trace_token_saving_span() -> None:
    trace = build_trace_from_audit_log(_log())
    saving = next(s for s in trace["spans"] if s["name"] == "token_saving.compress")
    assert saving["stage"] == "transform"
    assert saving["attributes"]["savings_pct"] == 12


def test_build_trace_failover_chain() -> None:
    details = (
        "trace_id=abc123def45678901234567890123456; Routed to llama3.2 via ollama "
        "|failover_chain=[{\"model\":\"gpt-4o\",\"upstream\":\"openai\",\"status\":\"failed\",\"error\":\"timeout\"},"
        "{\"model\":\"llama3.2\",\"upstream\":\"ollama\",\"status\":\"success\"}]"
    )
    trace = build_trace_from_audit_log(_log(details=details, resource="llama3.2 /chat"))
    failover_spans = [s for s in trace["spans"] if s["name"] == "llm.failover"]
    assert len(failover_spans) == 2
    assert failover_spans[0]["status"] == "error"
    assert failover_spans[1]["status"] == "ok"


def test_build_trace_blocked_ingress() -> None:
    trace = build_trace_from_audit_log(
        _log(
            status="blocked",
            action="Prompt Injection",
            details="trace_id=deadbeef; Ignore previous instructions detected",
            usage_metadata=None,
        )
    )
    policy = next(s for s in trace["spans"] if s["name"] == "policy.inspect")
    assert policy["status"] == "error"
