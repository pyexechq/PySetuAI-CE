"""Tests for telemetry facade aggregation (BL-076)."""

from datetime import UTC, datetime, timedelta

from app.services.telemetry_service import summarize_events, summarize_operations


def _event(
    status: str = "allowed",
    action: str = "LLM Request",
    risk: str = "low",
    model: str = "gpt-4o",
    total: int = 100,
    prompt: int = 60,
    completion: int = 40,
    when: datetime | None = None,
) -> tuple:
    meta = {"model": model, "total_tokens": total, "prompt_tokens": prompt, "completion_tokens": completion}
    return (status, action, risk, when or datetime.now(UTC), meta)


def _op_row(
    status: str = "allowed",
    action: str = "LLM Request",
    risk: str = "low",
    actor: str = "admin@acme.com",
    resource: str = "gpt-4o",
    total: int = 100,
    when: datetime | None = None,
) -> tuple:
    meta = {"model": "gpt-4o", "total_tokens": total, "prompt_tokens": 60, "completion_tokens": total - 60}
    return (status, action, risk, actor, resource, when or datetime.now(UTC), meta)


def test_summarize_events_counts_and_rates() -> None:
    rows = [
        _event(status="allowed"),
        _event(status="allowed"),
        _event(status="blocked", action="MCP Tool Call", risk="high"),
        _event(status="review", risk="medium"),
    ]
    result = summarize_events(rows, avg_latency_ms=120, p95_latency_ms=250, period_days=7)
    assert result["total_events"] == 4
    assert result["allowed"] == 2
    assert result["blocked"] == 1
    assert result["under_review"] == 1
    assert result["block_rate"] == 25.0
    assert result["avg_latency_ms"] == 120
    assert result["p95_latency_ms"] == 250
    assert result["active_models"] == 1
    assert result["total_tokens"] == 400
    assert result["total_cost_usd"] > 0


def test_summarize_events_by_action_and_risk() -> None:
    rows = [
        _event(status="blocked", action="LLM Request", risk="high"),
        _event(status="blocked", action="MCP Tool Call", risk="high"),
        _event(status="allowed", action="LLM Request", risk="low"),
    ]
    result = summarize_events(rows)
    actions = {item["action"]: item["count"] for item in result["by_action"]}
    risks = {item["risk"]: item["count"] for item in result["by_risk"]}
    assert actions == {"LLM Request": 2, "MCP Tool Call": 1}
    assert risks == {"high": 2, "low": 1}


def test_summarize_events_daily_trend() -> None:
    now = datetime.now(UTC)
    rows = [
        _event(status="blocked", when=now - timedelta(days=1)),
        _event(status="allowed", when=now),
    ]
    result = summarize_events(rows, period_days=7)
    assert len(result["daily_trend"]) == 2
    blocked_days = [point for point in result["daily_trend"] if point["blocked"] > 0]
    assert len(blocked_days) == 1


def test_summarize_events_empty() -> None:
    result = summarize_events([], period_days=7)
    assert result["total_events"] == 0
    assert result["block_rate"] == 0.0
    assert result["daily_trend"] == []


def test_summarize_operations_token_breakdown() -> None:
    rows = [
        _op_row(status="allowed", total=100),
        _op_row(status="blocked", total=50),
    ]
    result = summarize_operations(rows, p50_latency_ms=60, p95_latency_ms=250)
    assert result["requests_total"] == 2
    assert result["requests_allowed"] == 1
    assert result["requests_blocked"] == 1
    assert result["tokens_total"] == 150
    assert result["prompt_tokens"] == 120
    assert result["completion_tokens"] == 30
    assert result["p50_latency_ms"] == 60
    assert result["p95_latency_ms"] == 250
    assert result["block_rate"] == 50.0


def test_summarize_operations_recent_blocked_capped() -> None:
    rows = [_op_row(status="blocked", resource=f"res-{i}") for i in range(30)]
    result = summarize_operations(rows)
    assert len(result["recent_blocked"]) == 20


def test_summarize_operations_by_status() -> None:
    rows = [
        _op_row(status="allowed"),
        _op_row(status="blocked"),
        _op_row(status="review"),
    ]
    result = summarize_operations(rows)
    statuses = {item["status"]: item["count"] for item in result["by_status"]}
    assert statuses == {"allowed": 1, "blocked": 1, "review": 1}
