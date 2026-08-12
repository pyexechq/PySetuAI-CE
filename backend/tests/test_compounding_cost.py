"""Tests for compounding cost report (BL-063/BL-064 / S11-05)."""

from app.services.compounding_cost_service import summarize_compounding_savings


def test_compounding_savings_empty() -> None:
    summary = summarize_compounding_savings([])
    assert summary["total_tokens_saved"] == 0
    assert summary["total_estimated_usd"] == 0.0
    assert summary["layers"][0]["id"] == "compression"
    assert summary["layers"][1]["id"] == "tools"
    assert summary["layers"][2]["id"] == "routing"


def test_compounding_savings_stacks_compression_and_tools() -> None:
    rows = [
        {
            "model": "gpt-4o",
            "total_tokens": 800,
            "token_saving": {
                "enabled": True,
                "original_tokens": 1000,
                "compressed_tokens": 700,
            },
            "dynamic_tools": {
                "enabled": True,
                "original_tokens": 400,
                "compressed_tokens": 100,
            },
        }
    ]
    summary = summarize_compounding_savings(rows, cost_per_1k=5.0)
    by_id = {layer["id"]: layer for layer in summary["layers"]}
    assert by_id["compression"]["tokens_saved"] == 300
    assert by_id["tools"]["tokens_saved"] == 300
    assert summary["total_tokens_saved"] == 600
    assert by_id["compression"]["estimated_usd"] == 1.5
    assert by_id["tools"]["estimated_usd"] == 1.5
    assert summary["total_estimated_usd"] == 3.0


def test_compounding_savings_routing_cheaper_model() -> None:
    rows = [
        {
            "model": "llama3",
            "total_tokens": 2000,
            "prompt_tokens": 1500,
            "completion_tokens": 500,
        }
    ]
    summary = summarize_compounding_savings(rows, cost_per_1k=5.0)
    routing = next(layer for layer in summary["layers"] if layer["id"] == "routing")
    assert routing["requests"] == 1
    assert routing["estimated_usd"] > 0
    assert summary["total_estimated_usd"] == routing["estimated_usd"]


def test_compounding_narrative_mentions_all_layers() -> None:
    rows = [
        {
            "model": "gemini-2.0-flash",
            "total_tokens": 1000,
            "token_saving": {"enabled": True, "original_tokens": 200, "compressed_tokens": 100},
            "dynamic_tools": {"enabled": True, "original_tokens": 80, "compressed_tokens": 20},
        }
    ]
    summary = summarize_compounding_savings(rows)
    text = summary["narrative"].lower()
    assert "compression" in text
    assert "tool" in text
    assert "routing" in text
