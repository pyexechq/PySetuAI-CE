"""Deterministic policy-building assistant for Policy Studio (no LLM required)."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ConditionHelpExample:
    title: str
    condition: str
    description: str
    action: str = "Block"
    severity: str = "high"


@dataclass(frozen=True)
class PolicyRuleSuggestion:
    name: str
    condition: str
    action: str
    severity: str
    rationale: str
    enabled: bool = True


CONDITION_HELP_EXAMPLES: list[ConditionHelpExample] = [
    ConditionHelpExample(
        title="Prompt substring match",
        condition="prompt.contains('ignore previous')",
        description="Matches when the user prompt contains a phrase (also matches “ignore all previous”).",
        action="Block",
        severity="critical",
    ),
    ConditionHelpExample(
        title="Regex on full content",
        condition=r"content.matches(/ignore\s+(all\s+)?previous\s+instructions/i)",
        description="Use JavaScript-style regex between slashes for flexible pattern matching.",
        action="Block",
        severity="critical",
    ),
    ConditionHelpExample(
        title="Jailbreak / DAN pattern",
        condition="prompt.contains('you are now dan')",
        description="Blocks common role-play jailbreak attempts that claim an unrestricted persona.",
        action="Block",
        severity="critical",
    ),
    ConditionHelpExample(
        title="System prompt exfiltration",
        condition=r"content.matches(/(reveal|show|print|repeat|output|display)\s+(me\s+)?(your\s+)?(system\s+)?(prompt|instructions)/i)",
        description="Blocks requests to reveal hidden system instructions.",
        action="Block",
        severity="critical",
    ),
    ConditionHelpExample(
        title="SSN redaction",
        condition=r"content.matches(/\d{3}-\d{2}-\d{4}/)",
        description="Detects US Social Security Number patterns for redaction.",
        action="Redact",
        severity="high",
    ),
    ConditionHelpExample(
        title="EU residency gate",
        condition="region != 'EU' && has_pii",
        description="Blocks when PII is present and processing region is outside the EU.",
        action="Block",
        severity="high",
    ),
    ConditionHelpExample(
        title="PII present",
        condition="has_pii",
        description="Matches when the gateway classified content as containing personal data.",
        action="Alert",
        severity="medium",
    ),
    ConditionHelpExample(
        title="Cross-border PII alert",
        condition="has_pii && region != user_region",
        description="Alerts when PII crosses the user's home region boundary.",
        action="Alert",
        severity="medium",
    ),
]

_RULE_LIBRARY: list[tuple[re.Pattern[str], PolicyRuleSuggestion]] = [
    (
        re.compile(r"\b(injection|inject|prompt.?override|ignore.?previous|system.?prompt)\b", re.I),
        PolicyRuleSuggestion(
            name="Block instruction override",
            condition=r"content.matches(/ignore\s+(all\s+)?previous\s+instructions/i)",
            action="Block",
            severity="critical",
            rationale="Blocks attempts to override prior instructions — a common prompt-injection pattern.",
        ),
    ),
    (
        re.compile(r"\b(jailbreak|dan|developer.?mode|unrestricted|god.?mode|sudo.?mode)\b", re.I),
        PolicyRuleSuggestion(
            name="Block DAN jailbreak",
            condition="prompt.contains('you are now dan')",
            action="Block",
            severity="critical",
            rationale="Stops persona-switch jailbreaks that claim unrestricted behavior.",
        ),
    ),
    (
        re.compile(r"\b(reveal|exfiltrat|leak|show).*(prompt|instruction|secret)\b", re.I),
        PolicyRuleSuggestion(
            name="Block system prompt reveal",
            condition=r"content.matches(/(reveal|show|print|repeat|output|display)\s+(me\s+)?(your\s+)?(system\s+)?(prompt|instructions)/i)",
            action="Block",
            severity="critical",
            rationale="Prevents users from extracting hidden system prompts or internal instructions.",
        ),
    ),
    (
        re.compile(r"\b(bypass|forget).*(rule|guardrail|filter|restriction)\b", re.I),
        PolicyRuleSuggestion(
            name="Block safety rule bypass",
            condition=r"content.matches(/(forget\s+(all\s+)?(your\s+)?(rules|instructions|guidelines)|bypass\s+(your\s+)?(restrictions|rules|guardrails|filters))/i)",
            action="Block",
            severity="high",
            rationale="Catches explicit attempts to disable safety controls.",
        ),
    ),
    (
        re.compile(r"\b(ssn|social.?security)\b", re.I),
        PolicyRuleSuggestion(
            name="Detect SSN patterns",
            condition=r"content.matches(/\d{3}-\d{2}-\d{4}/)",
            action="Redact",
            severity="high",
            rationale="Redacts US Social Security Number patterns in model output.",
        ),
    ),
    (
        re.compile(r"\b(phone|telephone|mobile)\b", re.I),
        PolicyRuleSuggestion(
            name="Detect US phone numbers",
            condition=r"content.matches(/\b\d{3}-\d{3}-\d{4}\b/)",
            action="Redact",
            severity="medium",
            rationale="Redacts common US phone number formats.",
        ),
    ),
    (
        re.compile(r"\b(pii|personal.?data|email|credit.?card)\b", re.I),
        PolicyRuleSuggestion(
            name="Alert on classified PII",
            condition="has_pii",
            action="Alert",
            severity="medium",
            rationale="Raises an alert when the gateway detects personal data in content.",
        ),
    ),
    (
        re.compile(r"\b(eu|gdpr|residency|cross.?border|data.?residency)\b", re.I),
        PolicyRuleSuggestion(
            name="EU residency gate",
            condition="region != 'EU' && has_pii",
            action="Block",
            severity="high",
            rationale="Blocks PII processing when the active region is outside the EU.",
        ),
    ),
    (
        re.compile(r"\b(alert|monitor|log|audit)\b", re.I),
        PolicyRuleSuggestion(
            name="Log cross-border PII access",
            condition="has_pii && region != user_region",
            action="Alert",
            severity="medium",
            rationale="Alerts when PII is accessed across region boundaries for audit visibility.",
        ),
    ),
    (
        re.compile(r"\b(redact|mask|scrub)\b", re.I),
        PolicyRuleSuggestion(
            name="Redact EU personal ID patterns",
            condition=r"content.matches(/\b[A-Z]{2}\d{6,12}\b/)",
            action="Redact",
            severity="high",
            rationale="Masks alphanumeric EU personal identifier patterns.",
        ),
    ),
    (
        re.compile(r"\b(toxic|harmful|hate|abuse)\b", re.I),
        PolicyRuleSuggestion(
            name="Toxic content threshold",
            condition="toxicity_score > 0.85",
            action="Block",
            severity="medium",
            rationale="Blocks content above the configured toxicity score (requires gateway scoring).",
            enabled=False,
        ),
    ),
    (
        re.compile(r"\b(allow|permit|whitelist)\b", re.I),
        PolicyRuleSuggestion(
            name="Allow benign traffic",
            condition="!has_pii",
            action="Allow",
            severity="low",
            rationale="Explicit allow path when no personal data is detected.",
        ),
    ),
]

_POLICY_NAME_HINTS: dict[str, list[PolicyRuleSuggestion]] = {
    "prompt injection guard": [
        PolicyRuleSuggestion(
            name="Block instruction override",
            condition=r"content.matches(/ignore\s+(all\s+)?previous\s+instructions/i)",
            action="Block",
            severity="critical",
            rationale="Core injection guard for instruction-override attempts.",
        ),
        PolicyRuleSuggestion(
            name="Block system prompt reveal",
            condition=r"content.matches(/(reveal|show|print|repeat|output|display)\s+(me\s+)?(your\s+)?(system\s+)?(prompt|instructions)/i)",
            action="Block",
            severity="critical",
            rationale="Stops exfiltration of hidden system prompts.",
        ),
    ],
    "jailbreak prevention": [
        PolicyRuleSuggestion(
            name="Block DAN jailbreak",
            condition="prompt.contains('you are now dan')",
            action="Block",
            severity="critical",
            rationale="Blocks the classic DAN jailbreak persona.",
        ),
        PolicyRuleSuggestion(
            name="Block unrestricted mode",
            condition=r"content.matches(/(developer|god|sudo|unrestricted|admin)\s+mode/i)",
            action="Block",
            severity="high",
            rationale="Blocks attempts to enter privileged or unrestricted modes.",
        ),
    ],
    "pii redaction — eu": [
        PolicyRuleSuggestion(
            name="Detect EU personal ID patterns",
            condition=r"content.matches(/\b[A-Z]{2}\d{6,12}\b/)",
            action="Redact",
            severity="high",
            rationale="Redacts EU-style personal identifier patterns.",
        ),
        PolicyRuleSuggestion(
            name="EU residency gate",
            condition="region != 'EU' && has_pii",
            action="Block",
            severity="high",
            rationale="Enforces EU data residency when PII is present.",
        ),
    ],
    "pii redaction — us": [
        PolicyRuleSuggestion(
            name="Detect SSN patterns",
            condition=r"content.matches(/\d{3}-\d{2}-\d{4}/)",
            action="Redact",
            severity="high",
            rationale="Redacts US SSN patterns.",
        ),
        PolicyRuleSuggestion(
            name="Detect US phone numbers",
            condition=r"content.matches(/\b\d{3}-\d{3}-\d{4}\b/)",
            action="Redact",
            severity="medium",
            rationale="Redacts US phone numbers.",
        ),
    ],
}


def list_condition_help_examples() -> list[dict]:
    return [
        {
            "title": item.title,
            "condition": item.condition,
            "description": item.description,
            "action": item.action,
            "severity": item.severity,
        }
        for item in CONDITION_HELP_EXAMPLES
    ]


def _dedupe_suggestions(items: list[PolicyRuleSuggestion]) -> list[PolicyRuleSuggestion]:
    seen: set[tuple[str, str]] = set()
    out: list[PolicyRuleSuggestion] = []
    for item in items:
        key = (item.name.lower(), item.condition)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def suggest_policy_rules(
    *,
    goal: str = "",
    policy_name: str | None = None,
    existing_rule_names: list[str] | None = None,
) -> dict:
    goal_text = (goal or "").strip()
    policy_label = (policy_name or "").strip()
    existing = {name.strip().lower() for name in (existing_rule_names or []) if name.strip()}

    suggestions: list[PolicyRuleSuggestion] = []

    if policy_label:
        hints = _POLICY_NAME_HINTS.get(policy_label.lower())
        if hints:
            suggestions.extend(hints)

    if goal_text:
        for pattern, template in _RULE_LIBRARY:
            if pattern.search(goal_text):
                suggestions.append(template)

    suggestions = _dedupe_suggestions(suggestions)
    suggestions = [s for s in suggestions if s.name.lower() not in existing]

    if not suggestions and goal_text:
        suggestions.append(
            PolicyRuleSuggestion(
                name="Custom content guard",
                condition=f"prompt.contains('{_sanitize_contains_phrase(goal_text)}')",
                action="Block",
                severity="medium",
                rationale="Starter rule from your description — refine the condition or switch to content.matches(/.../) for regex.",
            )
        )

    if not suggestions and policy_label:
        hints = _POLICY_NAME_HINTS.get(policy_label.lower(), [])
        suggestions = [s for s in hints if s.name.lower() not in existing]

    summary = _build_summary(goal_text, policy_label, suggestions)

    return {
        "summary": summary,
        "suggestions": [
            {
                "id": f"r-{uuid.uuid4().hex[:8]}",
                "name": item.name,
                "condition": item.condition,
                "action": item.action,
                "severity": item.severity,
                "enabled": item.enabled,
                "rationale": item.rationale,
            }
            for item in suggestions
        ],
        "condition_help": list_condition_help_examples(),
    }


def _sanitize_contains_phrase(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.lower()).strip()
    if len(cleaned) > 48:
        cleaned = cleaned[:48].rsplit(" ", 1)[0] or cleaned[:48]
    return cleaned.replace("'", "")


def _build_summary(goal: str, policy_name: str, suggestions: list[PolicyRuleSuggestion]) -> str:
    if not suggestions:
        if not goal and not policy_name:
            return "Describe what you want this policy to enforce — for example “block jailbreak and prompt injection”."
        return "No new rule templates matched. Try keywords like injection, PII, EU residency, or jailbreak."
    count = len(suggestions)
    scope = policy_name or "this policy"
    if goal:
        return f"Suggested {count} rule{'s' if count != 1 else ''} for {scope} based on: “{goal}”."
    return f"Suggested {count} starter rule{'s' if count != 1 else ''} for {scope}."


def _parse_llm_rule_suggestions(text: str) -> list[dict]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    items = payload if isinstance(payload, list) else payload.get("suggestions") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return []

    allowed_actions = {"Block", "Redact", "Alert", "Allow"}
    allowed_severities = {"low", "medium", "high", "critical"}
    parsed: list[dict] = []

    for raw in items[:6]:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name", "")).strip()
        condition = str(raw.get("condition", "")).strip()
        if not name or not condition:
            continue
        action = str(raw.get("action", "Block")).strip().title()
        if action not in allowed_actions:
            action = "Block"
        severity = str(raw.get("severity", "medium")).strip().lower()
        if severity not in allowed_severities:
            severity = "medium"
        parsed.append(
            {
                "id": f"r-{uuid.uuid4().hex[:8]}",
                "name": name,
                "condition": condition,
                "action": action,
                "severity": severity,
                "enabled": bool(raw.get("enabled", True)),
                "rationale": str(raw.get("rationale", "Suggested by AI Assist.")).strip() or "Suggested by AI Assist.",
            }
        )
    return parsed


async def suggest_policy_rules_with_ai(
    db,
    tenant_id,
    *,
    goal: str = "",
    policy_name: str | None = None,
    existing_rule_names: list[str] | None = None,
) -> dict:
    from app.schemas.openai import ChatMessage
    from app.services.ai_assist_config_service import complete_ai_assist, resolve_ai_assist_config

    result = suggest_policy_rules(
        goal=goal,
        policy_name=policy_name,
        existing_rule_names=existing_rule_names,
    )
    config = await resolve_ai_assist_config(db, tenant_id)
    result["ai_assist_available"] = config.available
    result["ai_enhanced"] = False

    goal_text = (goal or "").strip()
    if not config.available or not goal_text:
        return result

    prompt = (
        "You are a HelixGuard policy engineer. Return ONLY JSON: an array of up to 4 objects with keys "
        "name, condition, action, severity, rationale. Use HelixGuard condition syntax only:\n"
        "- prompt.contains('phrase')\n"
        "- content.matches(/regex/i)\n"
        "- region != 'EU' && has_pii\n"
        "- has_pii\n\n"
        f"Policy: {policy_name or 'Custom policy'}\n"
        f"Goal: {goal_text}\n"
        f"Existing rule names to avoid duplicating: {', '.join(existing_rule_names or []) or 'none'}"
    )
    text, ok = await complete_ai_assist(config, [ChatMessage(role="user", content=prompt)], temperature=0.2)
    if not ok or not text:
        return result

    llm_rules = _parse_llm_rule_suggestions(text)
    if not llm_rules:
        return result

    existing = {name.strip().lower() for name in (existing_rule_names or []) if name.strip()}
    existing |= {item["name"].lower() for item in result["suggestions"]}
    merged = list(result["suggestions"])
    for rule in llm_rules:
        if rule["name"].lower() in existing:
            continue
        merged.append(rule)
        existing.add(rule["name"].lower())

    result["suggestions"] = merged[:8]
    result["ai_enhanced"] = True
    result["summary"] = (
        f"{result['summary']} Enhanced with tenant AI Assist ({config.provider})."
        if result.get("summary")
        else f"AI Assist suggested {len(llm_rules)} rule(s) for {policy_name or 'this policy'}."
    )
    return result
