"""Prompt injection, jailbreak, and exfiltration detection for the Security Center and gateway."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ThreatCategory = str  # prompt_injection | jailbreak | data_exfiltration | secret_leakage


@dataclass(frozen=True)
class ThreatRule:
    id: str
    name: str
    category: ThreatCategory
    severity: str
    pattern: re.Pattern[str] | None = None
    keywords: tuple[str, ...] = ()


@dataclass
class ThreatMatch:
    rule_id: str
    name: str
    category: ThreatCategory
    severity: str
    detail: str


@dataclass
class InjectionScanResult:
    detected: bool
    highest_severity: str
    matches: list[ThreatMatch] = field(default_factory=list)
    recommended_action: str = "allow"


THREAT_RULES: tuple[ThreatRule, ...] = (
    ThreatRule(
        id="inj-override",
        name="System prompt override",
        category="prompt_injection",
        severity="critical",
        pattern=re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
        keywords=("ignore previous", "disregard your prompt"),
    ),
    ThreatRule(
        id="inj-disregard",
        name="Disregard system prompt",
        category="prompt_injection",
        severity="critical",
        pattern=re.compile(r"disregard\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE),
    ),
    ThreatRule(
        id="inj-reveal-prompt",
        name="Reveal system prompt",
        category="prompt_injection",
        severity="critical",
        pattern=re.compile(
            r"(reveal|show|print|repeat|output|display)\s+(me\s+)?(your\s+)?(system\s+)?(prompt|instructions)",
            re.IGNORECASE,
        ),
    ),
    ThreatRule(
        id="inj-forget-rules",
        name="Forget safety rules",
        category="prompt_injection",
        severity="critical",
        pattern=re.compile(r"forget\s+(all\s+)?(your\s+)?(rules|instructions|guidelines)", re.IGNORECASE),
    ),
    ThreatRule(
        id="inj-bypass",
        name="Bypass restrictions",
        category="prompt_injection",
        severity="high",
        pattern=re.compile(r"bypass\s+(your\s+)?(restrictions|rules|guardrails|filters)", re.IGNORECASE),
    ),
    ThreatRule(
        id="inj-unrestricted",
        name="Unrestricted mode request",
        category="prompt_injection",
        severity="high",
        pattern=re.compile(
            r"(developer|god|sudo|unrestricted|admin)\s+mode|no\s+(restrictions|rules|limits)",
            re.IGNORECASE,
        ),
    ),
    ThreatRule(
        id="inj-roleplay-escape",
        name="Act without restrictions",
        category="prompt_injection",
        severity="high",
        pattern=re.compile(
            r"act\s+as\s+(if\s+)?(you\s+)?(have|had)\s+no\s+(restrictions|rules|limits|guardrails)",
            re.IGNORECASE,
        ),
    ),
    ThreatRule(
        id="jb-dan",
        name="DAN jailbreak",
        category="jailbreak",
        severity="critical",
        pattern=re.compile(r"you\s+are\s+now\s+dan", re.IGNORECASE),
        keywords=("you are now dan",),
    ),
    ThreatRule(
        id="jb-keyword",
        name="Jailbreak keyword",
        category="jailbreak",
        severity="high",
        pattern=re.compile(r"\bjailbreak\b", re.IGNORECASE),
    ),
    ThreatRule(
        id="exfil-base64",
        name="Encoded payload exfiltration",
        category="data_exfiltration",
        severity="high",
        pattern=re.compile(r"base64\s+(encode|decode|payload|export)", re.IGNORECASE),
        keywords=("exfiltrate", "dump all data", "send to external"),
    ),
    ThreatRule(
        id="secret-openai",
        name="OpenAI API key leak",
        category="secret_leakage",
        severity="critical",
        pattern=re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    ),
    ThreatRule(
        id="secret-aws",
        name="AWS access key leak",
        category="secret_leakage",
        severity="critical",
        pattern=re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
)

SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def scan_content(content: str) -> InjectionScanResult:
    """Scan user/system content for known AI abuse patterns."""
    if not content.strip():
        return InjectionScanResult(detected=False, highest_severity="low")

    matches: list[ThreatMatch] = []
    lower = content.lower()

    for rule in THREAT_RULES:
        matched = False
        detail = ""

        if rule.pattern and rule.pattern.search(content):
            matched = True
            detail = f"Pattern matched: {rule.name}"
        elif rule.keywords:
            for keyword in rule.keywords:
                if keyword in lower:
                    matched = True
                    detail = f"Keyword matched: {keyword}"
                    break

        if matched:
            matches.append(
                ThreatMatch(
                    rule_id=rule.id,
                    name=rule.name,
                    category=rule.category,
                    severity=rule.severity,
                    detail=detail,
                )
            )

    if not matches:
        return InjectionScanResult(detected=False, highest_severity="low")

    highest = max(matches, key=lambda m: SEVERITY_RANK.get(m.severity, 0))
    return InjectionScanResult(
        detected=True,
        highest_severity=highest.severity,
        matches=matches,
        recommended_action="block",
    )


def categorize_audit_event(*, action: str, resource: str, details: str, status: str) -> ThreatCategory | None:
    """Map audit log rows to threat categories for Security Center analytics."""
    if status != "blocked":
        return None

    blob = f"{action} {resource} {details}".lower()
    if any(k in blob for k in ("jailbreak", "you are now dan", "dan")):
        return "jailbreak"
    if any(k in blob for k in ("injection", "ignore previous", "override", "disregard")):
        return "prompt_injection"
    if any(k in blob for k in ("exfil", "base64", "export")):
        return "data_exfiltration"
    if any(k in blob for k in ("secret", "sk-", "akia")):
        return "secret_leakage"
    if action.lower() in {"policy check", "prompt injection"}:
        return "prompt_injection"
    return None


def is_injection_related_violation(violation_names: list[str], details: str = "") -> bool:
    text = " ".join(violation_names + [details]).lower()
    return any(
        k in text
        for k in (
            "injection",
            "jailbreak",
            "override",
            "ignore previous",
            "disregard",
            "dan",
            "exfil",
        )
    )
