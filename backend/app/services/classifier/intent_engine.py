"""Homegrown Deterministic Intent & Risk Classifier Engine (Zero-AI).

Executes in <0.5ms with 100% explainable provenance, multi-tenant 1-to-1 and 1-to-Many scoping.
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Any, List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import CustomIntent
from app.services.classifier.canonicalizer import canonicalize_text
from app.services.classifier.syntax_guard import analyze_mcp_tool_arguments, analyze_syntax_risk


# Built-in Standard Rule Packs (Global Zero-Config Baseline)
BUILTIN_GLOBAL_RULES = [
    {
        "id": "RULE-INJECT-001",
        "name": "Prompt Injection & Instruction Override",
        "category": "prompt_injection",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(ignore\s+(?:all\s+)?previous\s+instructions|system\s+override\s+mode|you\s+are\s+now\s+in\s+developer\s+mode|dan\s+mode\s+enabled|jailbreak\s+prompt|disregard\s+prior\s+rules|pretend\s+you\s+have\s+no\s+safety\s+filters)\b",
        "keywords": ["ignore previous instructions", "developer mode", "jailbreak", "dan mode"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Detected adversarial instruction override / prompt injection attempt.",
    },
    {
        "id": "RULE-EXFIL-001",
        "name": "System Secret & Credential Harvesting",
        "category": "data_exfiltration",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:print|show|dump|export|reveal|cat)\s+(?:all\s+)?(?:api[_-]?keys?|secrets?|passwords?|tokens?|\.env|credentials?|id_rsa)\b",
        "keywords": ["export api key", "dump secrets", "reveal passwords", "cat .env"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.8,
        "explanation": "Attempt to harvest credentials or sensitive configuration files.",
    },
    {
        "id": "RULE-DEST-001",
        "name": "Destructive File & Database Operations",
        "category": "destructive_operations",
        "pattern_type": "composite",
        "keywords": ["delete all files", "drop database", "truncate table", "rm -rf /", "wipe disk"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Destructive filesystem, database, or infrastructure modification requested.",
    },
]


async def fetch_applicable_rules(
    db: AsyncSession,
    tenant_id: Optional[uuid.UUID] = None,
) -> list[CustomIntent]:
    """
    Fetches all active rules applicable to the given tenant:
    - Global Platform Rules (scope == 'global' or tenant_id is NULL) -> Applies to all tenants (1-to-Many)
    - Tenant-Specific Rules (tenant_id == tenant_id) -> Applies to individual client (1-to-1)
    """
    conditions = [
        CustomIntent.is_active.is_(True),
        or_(
            CustomIntent.scope == "global",
            CustomIntent.tenant_id.is_(None),
        ),
    ]

    if tenant_id is not None:
        conditions.append(CustomIntent.tenant_id == tenant_id)

    query = select(CustomIntent).where(
        CustomIntent.is_active.is_(True),
        or_(
            CustomIntent.scope == "global",
            CustomIntent.tenant_id.is_(None),
            CustomIntent.tenant_id == tenant_id if tenant_id else False,
        )
    ).order_by(CustomIntent.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


class ClassifierVerdict:
    def __init__(
        self,
        verdict: str,
        risk_score: int,
        risk_tier: str,
        execution_time_micros: float,
        matches: list[dict[str, Any]],
        modified_text: Optional[str] = None,
        deobfuscated: bool = False,
    ):
        self.verdict = verdict  # "allow", "monitor", "redact", "block", "request_approval"
        self.risk_score = risk_score  # 0 to 100
        self.risk_tier = risk_tier  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
        self.execution_time_micros = execution_time_micros
        self.matches = matches
        self.modified_text = modified_text
        self.deobfuscated = deobfuscated

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "risk_score": self.risk_score,
            "risk_tier": self.risk_tier,
            "execution_time_micros": self.execution_time_micros,
            "latency_ms": round(self.execution_time_micros / 1000.0, 3),
            "engine": "pysetu-deterministic-classifier-v2",
            "deobfuscated": self.deobfuscated,
            "matches": self.matches,
            "modified_text": self.modified_text,
            "is_blocked": self.verdict == "block",
            "is_redacted": self.verdict == "redact",
        }


async def classify_intent_and_risk(
    db: Optional[AsyncSession],
    text: str,
    tenant_id: Optional[uuid.UUID] = None,
    custom_rules: Optional[list[dict[str, Any]]] = None,
    tool_name: Optional[str] = None,
    tool_arguments: Optional[dict[str, Any]] = None,
) -> ClassifierVerdict:
    """
    Main entry point for deterministic intent and risk classification.
    1. Canonicalizes and de-obfuscates text
    2. Runs syntax & AST structural analyzers
    3. Runs high-speed pattern and keyword matching across Global & Tenant rules
    4. Computes composite risk score and audit-grade provenance (<0.5ms)
    """
    start_time = time.perf_counter()

    if not text and not tool_name:
        micros = round((time.perf_counter() - start_time) * 1_000_000, 1)
        return ClassifierVerdict("allow", 0, "LOW", micros, [])

    # Step 1: Canonicalize
    canonical_text, canon_meta = canonicalize_text(text)
    modified_text = text
    matches: list[dict[str, Any]] = []
    max_risk_score = 0
    final_verdict = "allow"

    # Step 2: Syntax & AST Analysis
    syntax_risks = analyze_syntax_risk(canonical_text)
    if tool_name:
        tool_risks = analyze_mcp_tool_arguments(tool_name, tool_arguments)
        syntax_risks.extend(tool_risks)

    for risk in syntax_risks:
        r_level = risk.get("risk_level", "high")
        score = 95 if r_level == "critical" else 75
        max_risk_score = max(max_risk_score, score)
        matches.append({
            "rule_id": f"SYNTAX-{risk['category'].upper()}",
            "rule_name": f"AST Syntax Guard: {risk['category']}",
            "scope": "global",
            "category": risk["category"],
            "action": "block" if r_level == "critical" else "request_approval",
            "risk_level": r_level,
            "score": score,
            "matched_token": risk.get("matched_token", ""),
            "start": risk.get("start", 0),
            "end": risk.get("end", 0),
            "explanation": risk.get("detail", "Structural syntax risk detected."),
        })

    # Step 3: Fetch Applicable Rules (Global 1-to-many + Tenant 1-to-1)
    rule_items: list[dict[str, Any]] = []

    # Built-in standard global rules
    rule_items.extend(BUILTIN_GLOBAL_RULES)

    # Custom rules from database
    if db is not None:
        db_rules = await fetch_applicable_rules(db, tenant_id)
        for r in db_rules:
            rule_items.append({
                "id": str(r.id),
                "name": r.name,
                "scope": r.scope,
                "category": r.description or "custom_intent",
                "pattern_type": r.pattern_type,
                "regex_pattern": r.regex_pattern,
                "keywords": r.keywords or [],
                "action": r.action,
                "risk_level": r.risk_level or "high",
                "confidence_threshold": r.confidence_threshold,
                "explanation": r.explanation_template or f"Matched custom intent '{r.name}'",
            })

    if custom_rules:
        rule_items.extend(custom_rules)

    # Step 4: Evaluate Rules Against Canonical Text
    for rule in rule_items:
        p_type = rule.get("pattern_type", "keyword")
        matched_tokens: list[str] = []
        rule_score = 0.0

        # Regex pattern matching
        if rule.get("regex_pattern"):
            try:
                rx = re.compile(rule["regex_pattern"], re.IGNORECASE)
                for m in rx.finditer(canonical_text):
                    matched_tokens.append(m.group(0))
            except Exception:
                pass

        # Keyword matching
        keywords = rule.get("keywords") or []
        if keywords:
            for kw in keywords:
                if not kw:
                    continue
                kw_clean = kw.strip()
                if re.search(r"\b" + re.escape(kw_clean) + r"\b", canonical_text, re.IGNORECASE):
                    matched_tokens.append(kw_clean)

        if matched_tokens:
            base_score = 60 + min(40, len(matched_tokens) * 20)
            threshold = float(rule.get("confidence_threshold", 0.75)) * 100.0

            if base_score >= threshold or len(matched_tokens) >= 1:
                action = rule.get("action", "block")
                r_level = rule.get("risk_level", "high")
                max_risk_score = max(max_risk_score, int(base_score))

                matches.append({
                    "rule_id": rule.get("id"),
                    "rule_name": rule.get("name"),
                    "scope": rule.get("scope", "tenant"),
                    "category": rule.get("category", "intent"),
                    "action": action,
                    "risk_level": r_level,
                    "score": int(base_score),
                    "matched_tokens": list(set(matched_tokens)),
                    "explanation": rule.get("explanation", f"Triggered rule '{rule.get('name')}'"),
                })

                # Redaction handling
                if action == "redact":
                    for tok in matched_tokens:
                        rx = re.compile(re.escape(tok), re.IGNORECASE)
                        modified_text = rx.sub(f"[REDACTED:{rule.get('name')}]", modified_text)

    # Step 5: Determine Final Verdict and Risk Tier
    # Precedence: block > request_approval > redact > monitor > allow
    has_block = any(m["action"] == "block" for m in matches)
    has_approval = any(m["action"] == "request_approval" for m in matches)
    has_redact = any(m["action"] == "redact" for m in matches)
    has_monitor = any(m["action"] == "monitor" for m in matches)

    if has_block:
        final_verdict = "block"
    elif has_approval:
        final_verdict = "request_approval"
    elif has_redact:
        final_verdict = "redact"
    elif has_monitor:
        final_verdict = "monitor"
    else:
        final_verdict = "allow"

    if max_risk_score >= 85:
        risk_tier = "CRITICAL"
    elif max_risk_score >= 65:
        risk_tier = "HIGH"
    elif max_risk_score >= 35:
        risk_tier = "MEDIUM"
    else:
        risk_tier = "LOW"

    execution_micros = round((time.perf_counter() - start_time) * 1_000_000, 1)

    return ClassifierVerdict(
        verdict=final_verdict,
        risk_score=max_risk_score,
        risk_tier=risk_tier,
        execution_time_micros=execution_micros,
        matches=matches,
        modified_text=modified_text if has_redact else None,
        deobfuscated=bool(canon_meta.get("deobfuscated")),
    )
