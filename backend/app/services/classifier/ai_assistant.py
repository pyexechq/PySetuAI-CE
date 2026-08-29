"""AI-Powered Rule Generation Assistant for Intent & Risk Classifier.

Converts natural language policy requests into optimized deterministic regexes,
keyword dictionaries, AST definitions, and test payloads.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.openai import ChatMessage
from app.services.gemini_client import call_gemini


def _heuristic_rule_synthesis(goal: str) -> dict[str, Any]:
    """
    Fallback deterministic rule synthesizer when no LLM API is available.
    Extracts tokens, builds robust word boundary regex and keywords.
    """
    cleaned = re.sub(r"[^\w\s-]", " ", goal).strip()
    words = [w.lower() for w in cleaned.split() if len(w) > 2 and w.lower() not in {"the", "and", "for", "with", "that", "this", "from", "block", "prevent", "users", "trying"}]
    
    # Formulate keywords
    keywords = list(set(words))[:8]
    
    # Formulate regex with word boundaries
    if keywords:
        pattern = r"(?i)\b(?:" + "|".join(re.escape(k) for k in keywords) + r")\b"
    else:
        pattern = r"(?i)\b" + re.escape(cleaned[:30]) + r"\b"

    action = "block"
    if "redact" in goal.lower() or "mask" in goal.lower():
        action = "redact"
    elif "monitor" in goal.lower() or "log" in goal.lower() or "audit" in goal.lower():
        action = "monitor"

    risk_level = "high"
    if any(term in goal.lower() for term in ["critical", "drop", "delete", "destroy", "root", "secret", "exfil"]):
        risk_level = "critical"
    elif any(term in goal.lower() for term in ["low", "minor", "warn"]):
        risk_level = "low"

    return {
        "name": f"Rule: {goal[:40]}…",
        "description": goal,
        "action": action,
        "risk_level": risk_level,
        "pattern_type": "composite",
        "keywords": keywords,
        "regex_pattern": pattern,
        "confidence_threshold": 0.75,
        "explanation_template": f"Triggered intent rule for '{goal[:40]}'",
        "test_phrases": {
            "positive_matches": [f"User attempting to {goal[:30]}"],
            "negative_matches": ["Standard benign user request asking for general help."],
        },
    }


async def generate_classifier_rule_from_prompt(
    db: AsyncSession,
    tenant_id: Optional[Any],
    goal: str,
    target_scope: str = "global",
) -> dict[str, Any]:
    """
    Generates an optimized deterministic rule specification from a user's natural language goal.
    """
    if not goal or not goal.strip():
        raise ValueError("A natural language goal is required to generate a classifier rule.")

    trimmed_goal = goal.strip()

    # Attempt AI synthesis if Gemini API key configured
    if settings.gemini_api_key:
        try:
            prompt = f"""You are a cybersecurity expert building deterministic, high-speed regex & keyword rules for an AI Gateway Intent & Risk Firewall.

User Goal: "{trimmed_goal}"

Generate a valid JSON response with this exact structure:
{{
  "name": "Concise rule name (max 50 chars)",
  "description": "Clear description of risk",
  "action": "block" | "redact" | "monitor",
  "risk_level": "low" | "medium" | "high" | "critical",
  "pattern_type": "keyword" | "regex" | "composite",
  "keywords": ["list", "of", "4-10", "high-signal", "keywords"],
  "regex_pattern": "(?i)\\b(?:pattern1|pattern2)\\b",
  "confidence_threshold": 0.75,
  "explanation_template": "Clear explanation for audit logs",
  "test_phrases": {{
    "positive_matches": ["2 realistic attack/risk test prompts that MUST trigger this rule"],
    "negative_matches": ["2 benign normal prompts that MUST NOT trigger this rule"]
  }}
}}
Output ONLY valid raw JSON without markdown code fences."""

            messages = [ChatMessage(role="user", content=prompt)]
            content, _ = await call_gemini(
                model=settings.gemini_default_model or "gemini-1.5-pro",
                messages=messages,
                api_key=settings.gemini_api_key,
                temperature=0.2,
            )
            raw_text = content.strip()
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
            parsed = json.loads(raw_text)
            parsed["scope"] = target_scope
            return parsed
        except Exception:
            pass

    # Fallback to deterministic synthesis
    result = _heuristic_rule_synthesis(trimmed_goal)
    result["scope"] = target_scope
    return result
