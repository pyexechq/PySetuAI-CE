"""Dynamic Cost Arbitrage & Complexity-Based Model Routing Engine.

Analyzes prompt complexity, token length, and task intent to dynamically
downgrade simple queries from expensive frontier models (GPT-4o, Sonnet, Gemini Pro)
to high-efficiency lightweight models (GPT-4o-Mini, Haiku, Gemini Flash),
slashing enterprise token expenditures by 85–97%.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Pricing per 1M Input Tokens ($ USD)
MODEL_PRICING_PER_M: dict[str, float] = {
    "gpt-4o": 2.50,
    "gpt-4": 30.00,
    "claude-3.5-sonnet": 3.00,
    "claude-3-opus": 15.00,
    "gemini-1.5-pro": 3.50,
    # Lightweight / Flash Tier
    "gpt-4o-mini": 0.15,
    "claude-3.5-haiku": 0.25,
    "gemini-1.5-flash": 0.075,
    "llama-3.2-3b-instruct": 0.05,
    "ollama": 0.00,
}

# Frontier -> Flash Model Target Map
ARBITRAGE_TARGET_MAP: dict[str, str] = {
    "gpt-4o": "gpt-4o-mini",
    "gpt-4": "gpt-4o-mini",
    "claude-3.5-sonnet": "claude-3.5-haiku",
    "claude-3-opus": "claude-3.5-haiku",
    "gemini-1.5-pro": "gemini-1.5-flash",
    "gemini-pro": "gemini-1.5-flash",
}

# Regex patterns indicating complex multi-step reasoning or code engineering tasks
COMPLEXITY_PATTERNS = [
    re.compile(r"```[\w]*\n", re.IGNORECASE),  # Code blocks
    re.compile(r"\b(step[-\s]by[-\s]step|chain[-\s]of[-\s]thought|prove\s+that|derive\s+the|architectural\s+design|solve\s+the\s+proof)\b", re.IGNORECASE),
    re.compile(r"\b(refactor\s+this|debug\s+the\s+following|stack\s+trace|memory\s+leak|reverse\s+engineer)\b", re.IGNORECASE),
]


@dataclass(frozen=True)
class ArbitrageDecision:
    should_arbitrate: bool
    original_model: str
    target_model: str
    savings_pct: float
    estimated_cost_original_usd: float
    estimated_cost_arbitrated_usd: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_arbitrate": self.should_arbitrate,
            "original_model": self.original_model,
            "target_model": self.target_model,
            "savings_pct": self.savings_pct,
            "estimated_cost_original_usd": round(self.estimated_cost_original_usd, 6),
            "estimated_cost_arbitrated_usd": round(self.estimated_cost_arbitrated_usd, 6),
            "reason": self.reason,
        }


def evaluate_cost_arbitrage(
    prompt_text: str,
    requested_model: str,
    estimated_prompt_tokens: int = 100,
    force_arbitrage: bool = False,
) -> ArbitrageDecision:
    """Evaluate whether an inbound prompt can be safely downgraded to save token budget."""
    norm_requested = requested_model.strip().lower()
    target_model = ARBITRAGE_TARGET_MAP.get(norm_requested)

    # If the requested model is already a budget/flash model or not in frontier map
    if not target_model:
        return ArbitrageDecision(
            should_arbitrate=False,
            original_model=requested_model,
            target_model=requested_model,
            savings_pct=0.0,
            estimated_cost_original_usd=0.0,
            estimated_cost_arbitrated_usd=0.0,
            reason="Requested model is already in high-efficiency tier or custom local model.",
        )

    # Complexity Checks
    word_count = len(prompt_text.split())
    has_code_or_complex_reasoning = any(pat.search(prompt_text) for pat in COMPLEXITY_PATTERNS)

    # If prompt requires deep reasoning or is large code refactor, preserve frontier model
    if not force_arbitrage and (word_count > 400 or has_code_or_complex_reasoning):
        return ArbitrageDecision(
            should_arbitrate=False,
            original_model=requested_model,
            target_model=requested_model,
            savings_pct=0.0,
            estimated_cost_original_usd=(estimated_prompt_tokens / 1_000_000) * MODEL_PRICING_PER_M.get(norm_requested, 2.50),
            estimated_cost_arbitrated_usd=(estimated_prompt_tokens / 1_000_000) * MODEL_PRICING_PER_M.get(norm_requested, 2.50),
            reason=f"High complexity detected ({word_count} words, code/reasoning markers present). Retaining frontier model '{requested_model}'.",
        )

    # Low complexity: Safe to arbitrate
    orig_price = MODEL_PRICING_PER_M.get(norm_requested, 2.50)
    target_price = MODEL_PRICING_PER_M.get(target_model, 0.15)
    cost_orig = (estimated_prompt_tokens / 1_000_000) * orig_price
    cost_arb = (estimated_prompt_tokens / 1_000_000) * target_price
    savings_pct = round(((orig_price - target_price) / orig_price) * 100.0, 1)

    return ArbitrageDecision(
        should_arbitrate=True,
        original_model=requested_model,
        target_model=target_model,
        savings_pct=savings_pct,
        estimated_cost_original_usd=cost_orig,
        estimated_cost_arbitrated_usd=cost_arb,
        reason=f"Low-complexity prompt ({word_count} words). Arbitrated {requested_model} → {target_model} saving {savings_pct}% on token costs.",
    )
