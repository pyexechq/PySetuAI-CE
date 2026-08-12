"""Compounding cost savings — routing + dynamic tools + token compression (S11-05)."""

from __future__ import annotations

from typing import Any

DEFAULT_COST_PER_1K = 0.005


def _usd(tokens: int, cost_per_1k: float) -> float:
    return round(max(0, tokens) / 1000 * cost_per_1k, 4)


def _layer_tokens_saved(payload: dict | None) -> int:
    if not isinstance(payload, dict) or not payload.get("enabled"):
        return 0
    before = int(payload.get("original_tokens") or 0)
    after = int(payload.get("compressed_tokens") or 0)
    return max(0, before - after)


def _model_rate(model: str, baseline: float) -> float:
    name = (model or "").lower()
    if any(token in name for token in ("llama", "ollama", "mistral", "qwen", "phi")):
        return 0.0
    if "gemini" in name:
        return round(baseline * 0.7, 6)
    if "claude" in name or "anthropic" in name:
        return round(baseline * 1.2, 6)
    return baseline


def _empty_layers() -> list[dict[str, Any]]:
    return [
        {"id": "compression", "label": "JSON/markdown compression", "tokens_saved": 0, "estimated_usd": 0.0, "requests": 0, "share_pct": 0.0},
        {"id": "tools", "label": "Dynamic MCP tool calling", "tokens_saved": 0, "estimated_usd": 0.0, "requests": 0, "share_pct": 0.0},
        {"id": "routing", "label": "Weighted / cheaper routing", "tokens_saved": 0, "estimated_usd": 0.0, "requests": 0, "share_pct": 0.0},
    ]


def summarize_compounding_savings(
    usage_rows: list[dict | None],
    *,
    cost_per_1k: float = DEFAULT_COST_PER_1K,
) -> dict[str, Any]:
    """Stack compression, tool-filter, and routing savings from audit usage_metadata."""
    compression_tokens = 0
    compression_requests = 0
    tool_tokens = 0
    tool_requests = 0
    routing_usd = 0.0
    routing_requests = 0
    routing_tokens = 0

    for row in usage_rows:
        if not isinstance(row, dict):
            continue
        saved_compression = _layer_tokens_saved(row.get("token_saving") if isinstance(row.get("token_saving"), dict) else None)
        if saved_compression:
            compression_tokens += saved_compression
            compression_requests += 1
        saved_tools = _layer_tokens_saved(row.get("dynamic_tools") if isinstance(row.get("dynamic_tools"), dict) else None)
        if saved_tools:
            tool_tokens += saved_tools
            tool_requests += 1

        model = str(row.get("model") or "")
        actual_rate = _model_rate(model, cost_per_1k)
        if actual_rate < cost_per_1k:
            tokens = int(row.get("total_tokens") or 0)
            if tokens > 0:
                routing_usd += _usd(tokens, cost_per_1k - actual_rate)
                routing_requests += 1
                routing_tokens += tokens

    compression_usd = _usd(compression_tokens, cost_per_1k)
    tools_usd = _usd(tool_tokens, cost_per_1k)
    routing_usd = round(routing_usd, 4)
    total_tokens = compression_tokens + tool_tokens
    total_usd = round(compression_usd + tools_usd + routing_usd, 4)

    layers = _empty_layers()
    layers[0].update(tokens_saved=compression_tokens, estimated_usd=compression_usd, requests=compression_requests)
    layers[1].update(tokens_saved=tool_tokens, estimated_usd=tools_usd, requests=tool_requests)
    layers[2].update(tokens_saved=routing_tokens, estimated_usd=routing_usd, requests=routing_requests)
    if total_usd > 0:
        for layer in layers:
            layer["share_pct"] = round((layer["estimated_usd"] / total_usd) * 100, 1)

    narrative = (
        f"Compounding savings this period: compression avoided {compression_tokens:,} tokens "
        f"(${compression_usd:.2f}), dynamic tool calling avoided {tool_tokens:,} tokens "
        f"(${tools_usd:.2f}), and cheaper routing saved ${routing_usd:.2f} across {routing_requests} request(s). "
        f"Stacked total: ${total_usd:.2f}."
    )
    return {
        "layers": layers,
        "total_tokens_saved": total_tokens,
        "total_estimated_usd": total_usd,
        "narrative": narrative,
    }


def compounding_table(summary: dict[str, Any]) -> tuple[list[str], list[list[Any]]]:
    columns = ["layer", "tokens_saved", "estimated_usd", "requests", "share_pct"]
    rows = [
        [layer["label"], layer["tokens_saved"], layer["estimated_usd"], layer["requests"], layer["share_pct"]]
        for layer in summary["layers"]
    ]
    rows.append(
        [
            "Total (compounding)",
            summary["total_tokens_saved"],
            summary["total_estimated_usd"],
            sum(int(layer["requests"]) for layer in summary["layers"]),
            100.0 if summary["total_estimated_usd"] else 0.0,
        ]
    )
    return columns, rows
