"""Tests for cost analytics aggregation (BL-072)."""

from datetime import UTC, datetime

from app.services.cost_analytics_service import summarize_usage_rows


def _meta(
    model: str = "gpt-4o",
    total: int = 100,
    prompt: int = 60,
    completion: int = 40,
    **extra,
) -> dict:
    body = {
        "model": model,
        "total_tokens": total,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "auth_type": "client_key",
        "client_api_key_name": "copilot",
    }
    body.update(extra)
    return body


def test_summarize_usage_rows_by_model_and_user() -> None:
    rows = [
        (_meta(total=100), datetime.now(UTC), "admin@acme.com"),
        (_meta(model="llama3.2", total=50), datetime.now(UTC), "dev@acme.com"),
    ]
    result = summarize_usage_rows(rows, period_days=7)
    assert result["summary"]["requests"] == 2
    assert result["summary"]["total_tokens"] == 150
    assert len(result["by_model"]) == 2
    assert len(result["by_user"]) == 2
    assert result["by_team"][0]["label"] == "copilot"


def test_summarize_usage_rows_daily_trend() -> None:
    day = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    rows = [(_meta(total=80), day, "user@acme.com")]
    result = summarize_usage_rows(rows, period_days=30)
    assert len(result["daily_trend"]) == 1
    assert result["daily_trend"][0]["total_tokens"] == 80
