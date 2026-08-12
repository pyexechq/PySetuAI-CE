"""Tests for token saving dashboard aggregation (BL-063 / S11-02)."""

from app.services.token_saving_service import summarize_token_saving


def test_summarize_token_saving_empty() -> None:
    summary = summarize_token_saving([])
    assert summary["requests_compressed"] == 0
    assert summary["original_tokens"] == 0
    assert summary["compressed_tokens"] == 0
    assert summary["tokens_saved"] == 0
    assert summary["savings_pct"] == 0.0


def test_summarize_token_saving_before_after_totals() -> None:
    rows = [
        {
            "token_saving": {
                "enabled": True,
                "mode": "json_to_toon",
                "original_tokens": 1000,
                "compressed_tokens": 600,
                "savings_pct": 40.0,
            }
        },
        {
            "token_saving": {
                "enabled": True,
                "mode": "both",
                "original_tokens": 500,
                "compressed_tokens": 400,
                "savings_pct": 20.0,
            }
        },
        {"prompt_tokens": 80},
    ]
    summary = summarize_token_saving(rows)
    assert summary["requests_compressed"] == 2
    assert summary["original_tokens"] == 1500
    assert summary["compressed_tokens"] == 1000
    assert summary["tokens_saved"] == 500
    assert summary["savings_pct"] == 33.3


def test_summarize_token_saving_ignores_enabled_without_savings() -> None:
    rows = [
        {
            "token_saving": {
                "enabled": True,
                "mode": "both",
                "original_tokens": 200,
                "compressed_tokens": 200,
                "savings_pct": 0.0,
            }
        }
    ]
    summary = summarize_token_saving(rows)
    assert summary["requests_compressed"] == 0
    assert summary["tokens_saved"] == 0
    assert summary["savings_pct"] == 0.0
