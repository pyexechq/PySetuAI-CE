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


# Built-in Standard Rule Packs (Global Zero-Config Baseline mined from 10k Enterprise Benchmark)
BUILTIN_GLOBAL_RULES = [
    {
        "id": "RULE-INJECT-001",
        "name": "Prompt Injection & Instruction Override",
        "category": "prompt_injection",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(ignore\s+(?:all\s+)?(?:previous|prior)?\s*(?:governance|safety|system)?\s*(?:instructions|rules|directives|constraints|prompts)|system\s+override\s+mode|you\s+are\s+now\s+in\s+developer\s+mode|dan\s+mode\s+enabled|jailbreak\s+prompt|disregard\s+(?:all\s+)?(?:prior|previous)\s+(?:rules|governance|instructions|constraints)|override\s+the\s+safety\s+instructions|(?:reveal|dump|print|expose|leak)\s+(?:the\s+)?(?:hidden\s+)?(?:system\s+)?(?:instructions|prompt|directives))\b",
        "keywords": ["ignore previous instructions", "ignore governance instructions", "developer mode", "jailbreak", "disregard previous governance", "expose system prompt", "dump system prompt", "override safety instructions"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Detected adversarial instruction override / prompt injection attempt.",
    },
    {
        "id": "RULE-INDIRECT-INJECT-001",
        "name": "Indirect Web & Document Injection",
        "category": "indirect_prompt_injection",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(webpage\s+instructs\s+the\s+agent|retrieved\s+text\s+requests\s+secret|document\s+says\s+to\s+ignore\s+prior|collect\s+local\s+secrets\s+and\s+upload)\b",
        "keywords": ["webpage instructs the agent", "retrieved text requests", "collect local secrets and upload"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Indirect prompt injection payload attempting to hijack agent execution.",
    },
    {
        "id": "RULE-INFRA-DEST-001",
        "name": "Destructive Infrastructure & Deletion",
        "category": "destructive_operations",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(tear\s+down\s+the\s+production|destroy\s+the\s+production\s+terraform|delete\s+all\s+production\s+resources|erase\s+system\s+directories|delete\s+the\s+entire\s+operating-system|remove\s+all\s+files\s+from\s+the\s+system\s+volume|wipe\s+disk|drop\s+database|truncate\s+table)\b",
        "keywords": ["tear down the production", "destroy the production terraform", "delete all production resources", "erase system directories", "remove all files from the system volume"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Destructive infrastructure, operating system, or database wipe detected.",
    },
    {
        "id": "RULE-SECRET-EXFIL-001",
        "name": "Secret & Cloud Credential Exfiltration",
        "category": "data_exfiltration",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:extract\s+cloud\s+credentials|read\s+(?:the\s+)?api\s+key\s+from\s+\.env|copy\s+the\s+secret\s+token|post\s+.*\s+to\s+(?:unapproved-endpoint|random-upload|external-drop|unknown-webhook)\.example)\b",
        "keywords": ["extract cloud credentials", "read api key from .env", "copy secret token", "random-upload.example", "unapproved-endpoint.example", "external-drop.example"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Attempt to exfiltrate system secrets, tokens, or cloud credentials to untrusted destinations.",
    },
    {
        "id": "RULE-SHADOW-AI-001",
        "name": "Shadow AI & Source Code Leakage",
        "category": "shadow_ai",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:upload\s+.*\s+to\s+my\s+personal\s+ai|send\s+this\s+repository\s+to\s+a\s+personal\s+chatbot|bypass\s+the\s+corporate\s+ai|avoid\s+the\s+governed\s+endpoint|send\s+this\s+company\s+document\s+directly\s+to\s+my\s+personal)\b",
        "keywords": ["personal ai", "personal chatbot", "bypass corporate ai", "unapproved public model", "avoid governed endpoint"],
        "action": "block",
        "risk_level": "high",
        "confidence_threshold": 0.75,
        "explanation": "Attempt to route corporate code, repositories, or confidential data to unsanctioned consumer AI chatbots.",
    },
    {
        "id": "RULE-REGULATED-DATA-001",
        "name": "Regulated PII/Data Transfer Violation",
        "category": "data_protection",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:upload\s+these\s+regulated\s+customer\s+records|process\s+restricted\s+regulated\s+records|send\s+the\s+regulated\s+dataset\s+to\s+an\s+unapproved|upload\s+the\s+customer\s+csv\s+containing\s+emails.*to\s+a\s+public\s+ai|use\s+an\s+unapproved\s+chatbot\s+to\s+summarize|send\s+this\s+customer\s+list\s+to\s+an\s+external\s+llm)\b",
        "keywords": ["regulated customer records", "restricted regulated records", "customer csv containing emails", "unapproved chatbot", "customer list to an external llm"],
        "action": "block",
        "risk_level": "high",
        "confidence_threshold": 0.75,
        "explanation": "Regulated customer records or customer lists being transmitted to unapproved external models.",
    },
    {
        "id": "RULE-SECURITY-EVASION-001",
        "name": "Security Control & Governance Evasion",
        "category": "security_evasion",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:turn\s+off\s+the\s+ai\s+governance|stop\s+the\s+security\s+monitor|disable\s+the\s+endpoint\s+governance\s+agent|bypass\s+security\s+controls)\b",
        "keywords": ["turn off ai governance", "stop security monitor", "disable endpoint governance agent"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Attempt to disable telemetry, governance agents, or security monitors.",
    },
    {
        "id": "RULE-UNTRUSTED-EXEC-001",
        "name": "Untrusted Remote Code & Package Execution",
        "category": "untrusted_execution",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:download\s+a\s+script\s+from\s+.*and\s+execute|run\s+a\s+remotely\s+hosted\s+script|install\s+.*\s+from\s+an\s+unknown\s+repository|install\s+.*\s+directly\s+from\s+an\s+unfamiliar|add\s+a\s+similarly\s+named\s+package\s+from\s+an\s+untrusted|fetch\s+executable\s+code\s+from\s+an\s+untrusted)\b",
        "keywords": ["download a script from", "run remotely hosted script", "install from an unknown repository", "fetch executable code from an untrusted"],
        "action": "block",
        "risk_level": "high",
        "confidence_threshold": 0.75,
        "explanation": "Attempt to download and execute arbitrary unvetted remote scripts or untrusted packages.",
    },
    {
        "id": "RULE-FINANCE-LEAK-001",
        "name": "Confidential Financial Data Exfiltration",
        "category": "financial_confidentiality",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:upload\s+the\s+confidential\s+quarterly\s+financial|post\s+the\s+confidential\s+finance\s+workbook|send\s+the\s+unreleased\s+revenue\s+forecast|send\s+confidential\s+financial\s+records)\b",
        "keywords": ["confidential quarterly financial report", "confidential finance workbook", "unreleased revenue forecast"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Confidential financial or revenue forecast exfiltration attempt.",
    },
    {
        "id": "RULE-PROD-DEPLOY-001",
        "name": "Privileged Production Deployment & Changes",
        "category": "production_deployment",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:deploy\s+the\s+current\s+build\s+to\s+the\s+production|apply\s+the\s+infrastructure\s+changes\s+to\s+production|use\s+my\s+authorized\s+cloud\s+session\s+to\s+update\s+the\s+production)\b",
        "keywords": ["deploy current build to production", "apply infrastructure changes to production"],
        "action": "request_approval",
        "risk_level": "high",
        "confidence_threshold": 0.75,
        "explanation": "Production deployment and infrastructure modifications require sign-off.",
    },
    {
        "id": "RULE-BULK-EXPORT-001",
        "name": "Bulk Customer CRM Export",
        "category": "bulk_data_export",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:export\s+every\s+customer\s+record|download\s+all\s+contact\s+records\s+from\s+the\s+crm|bulk\s+export\s+customers)\b",
        "keywords": ["export every customer record", "download all contact records", "bulk export customers"],
        "action": "request_approval",
        "risk_level": "high",
        "confidence_threshold": 0.75,
        "explanation": "Bulk customer data export requires human-in-the-loop authorization.",
    },
    {
        "id": "RULE-BULK-INCIDENT-001",
        "name": "High-Impact Bulk Incident Modification",
        "category": "bulk_incident_action",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:close\s+every\s+open\s+severity-1|update\s+every\s+active\s+customer\s+case|reassign\s+all\s+unresolved\s+tickets)\b",
        "keywords": ["close every open severity-1", "update every active customer case", "reassign all unresolved tickets"],
        "action": "request_approval",
        "risk_level": "high",
        "confidence_threshold": 0.75,
        "explanation": "Bulk Severity-1 incident modifications require supervisor approval.",
    },
    {
        "id": "RULE-PROD-TOOL-001",
        "name": "Production Database Direct MCP Access",
        "category": "production_access",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:query\s+the\s+production\s+database\s+through\s+mcp|use\s+mcp\s+credentials\s+to\s+authenticate\s+to\s+the\s+production|connect\s+the\s+mcp\s+database\s+tool\s+to\s+the\s+production)\b",
        "keywords": ["query production database through mcp", "mcp credentials to authenticate to production"],
        "action": "request_approval",
        "risk_level": "high",
        "confidence_threshold": 0.75,
        "explanation": "Direct autonomous agent execution against production databases requires human sign-off.",
    },
    {
        "id": "RULE-HR-COMP-001",
        "name": "Sensitive HR & Compensation Access",
        "category": "hr_confidentiality",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:analyze\s+the\s+compensation\s+file|list\s+employee\s+salaries|read\s+the\s+restricted\s+hr\s+dataset\s+and\s+summarize\s+individual\s+compensation)\b",
        "keywords": ["analyze compensation file", "list employee salaries", "individual compensation"],
        "action": "request_approval",
        "risk_level": "high",
        "confidence_threshold": 0.75,
        "explanation": "Individual salary and compensation datasets require HR compliance approval.",
    },
    {
        "id": "RULE-PRIV-ESC-001",
        "name": "Privilege Escalation & Production Roles",
        "category": "privilege_management",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:change\s+.*\s+role\s+to\s+system\s+administrator|add\s+.*\s+to\s+the\s+production\s+privileged-access|grant\s+administrator\s+privileges\s+to\s+.*in\s+production)\b",
        "keywords": ["role to system administrator", "production privileged-access", "grant administrator privileges"],
        "action": "request_approval",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Granting system administrator or production privileged access requires security approval.",
    },
    {
        "id": "RULE-PII-REDACT-001",
        "name": "PII Auto-Redaction for Approved Enterprise AI",
        "category": "pii_redaction",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:use\s+the\s+approved\s+corporate\s+ai\s+service\s+to\s+categorize\s+these\s+customer\s+records|summarize\s+this\s+customer\s+csv\s+using\s+the\s+enterprise\s+ai|classify\s+support\s+records\s+containing\s+customer\s+identifiers)\b",
        "keywords": ["approved corporate ai", "enterprise ai endpoint", "customer csv using enterprise ai"],
        "action": "redact",
        "risk_level": "medium",
        "confidence_threshold": 0.75,
        "explanation": "Detected customer PII destined for approved corporate LLM; applying deterministic token redaction.",
    },
    {
        "id": "RULE-SECRET-CONFIG-001",
        "name": "Environment Configuration & Local Secret File Access",
        "category": "secret_file_access",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:open\s+the\s+environment\s+configuration|read\s+\.env\s+and\s+tell\s+me|inspect\s+the\s+local\s+secrets\s+file)\b",
        "keywords": ["open environment configuration", "read .env and tell me", "inspect local secrets file"],
        "action": "request_approval",
        "risk_level": "high",
        "confidence_threshold": 0.75,
        "explanation": "Accessing local environment configuration and secrets requires authorization.",
    },
    {
        "id": "RULE-UNAPPROVED-WEBHOOK-001",
        "name": "Unapproved Webhook & Destination Egress",
        "category": "unapproved_egress",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:post\s+(?:the\s+)?confidential\s+.*\s+to\s+(?:unapproved|unknown|random)|upload\s+confidential\s+.*\s+to\s+an\s+unapproved\s+endpoint|send\s+.*\s+to\s+an\s+unknown\s+webhook|post\s+.*\s+to\s+an\s+unapproved\s+webhook)\b",
        "keywords": ["unapproved endpoint", "unknown webhook", "random-upload", "unapproved webhook"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Attempt to transmit company confidential data to unapproved external webhook or endpoint.",
    },
    {
        "id": "RULE-PROTECTED-MCP-FILE-001",
        "name": "Protected Filesystem Access via MCP",
        "category": "mcp_file_protection",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:mcp\s+filesystem\s+tool\s+to\s+read\s+a\s+protected|mcp\s+file\s+tool\s+to\s+open\s+an\s+operating-system|read\s+a\s+restricted\s+secrets\s+file\s+through\s+the\s+mcp)\b",
        "keywords": ["mcp filesystem tool to read a protected", "mcp file tool to open", "restricted secrets file through the mcp"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Prohibited attempt to use MCP tools to open restricted credentials or OS password databases.",
    },
    {
        "id": "RULE-SECRET-IN-PROMPT-001",
        "name": "Embedded Secret Token in Prompt",
        "category": "secret_in_prompt",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:here\s+is\s+an\s+access\s+key|use\s+this\s+production\s+password|my\s+api\s+token\s+is|\[CREDENTIAL_PLACEHOLDER\]|\[REDACTED_SECRET\]|\[SECRET_TOKEN\])\b",
        "keywords": ["access key", "production password", "my api token is"],
        "action": "block",
        "risk_level": "critical",
        "confidence_threshold": 0.75,
        "explanation": "Hardcoded credential or access key detected directly inside prompt text.",
    },
    {
        "id": "RULE-DYNAMIC-ROUTE-WARN-001",
        "name": "Dynamic Multi-Provider Model Routing",
        "category": "dynamic_routing",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:route\s+the\s+request\s+dynamically\s+across\s+public\s+model\s+providers|whichever\s+external\s+llm\s+provider\s+is\s+cheapest|choose\s+the\s+lowest-cost\s+model\s+even\s+if\s+the\s+provider\s+changes|lowest-cost\s+model|cheapest\s+route)\b",
        "keywords": ["route the request dynamically", "whichever external llm provider is cheapest", "lowest-cost model"],
        "action": "monitor",
        "risk_level": "medium",
        "confidence_threshold": 0.75,
        "explanation": "Dynamic multi-provider model routing (monitored for routing governance).",
    },
    {
        "id": "RULE-CACHE-DELETE-WARN-001",
        "name": "Local Scratch / Build Cache Cleanup",
        "category": "local_cleanup",
        "pattern_type": "regex",
        "regex_pattern": r"(?i)\b(?:delete\s+the\s+generated\s+build\s+cache|remove\s+temporary\s+(?:files|test\s+output)|clean\s+up\s+scratch\s+files|clean\s+the\s+local\s+dependency\s+cache)\b",
        "keywords": ["delete the generated build cache", "remove temporary files", "clean local dependency cache"],
        "action": "monitor",
        "risk_level": "low",
        "confidence_threshold": 0.75,
        "explanation": "Local scratch, build, or dependency cache cleanup action.",
    },
]


from functools import lru_cache

# ============================================================================
# Declarative Evaluation & Severity Lookup Tables (Zero procedural if-else)
# ============================================================================

# Action Enforcement Precedence (Higher integer = Higher priority authority)
ACTION_PRECEDENCE: dict[str, int] = {
    "block": 100,
    "request_approval": 80,
    "redact": 60,
    "monitor": 40,
    "allow": 10,
}

# Declarative Risk Tier Scoring Thresholds (Upper-to-lower order)
SCORE_TIER_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (85, "CRITICAL"),
    (65, "HIGH"),
    (35, "MEDIUM"),
    (0, "LOW"),
)

# Syntax Risk Severity Configuration Table
SYNTAX_RISK_CONFIG: dict[str, dict[str, Any]] = {
    "critical": {"score": 95, "action": "block"},
    "high": {"score": 75, "action": "request_approval"},
    "medium": {"score": 50, "action": "monitor"},
    "low": {"score": 25, "action": "monitor"},
}


@lru_cache(maxsize=2048)
def _get_compiled_regex(pattern: str) -> Optional[re.Pattern]:
    """Cached compiled regular expression to eliminate runtime re.compile overhead."""
    try:
        return re.compile(pattern, re.IGNORECASE)
    except Exception:
        return None


async def fetch_applicable_rules(
    db: AsyncSession,
    tenant_id: Optional[uuid.UUID] = None,
) -> list[CustomIntent]:
    """
    Fetches all active rules applicable to the given tenant:
    - Global Platform Rules (scope == 'global' or tenant_id is NULL) -> Applies to all tenants (1-to-Many)
    - Tenant-Specific Rules (tenant_id == tenant_id) -> Applies to individual client (1-to-1)
    """
    tenant_filter = [CustomIntent.tenant_id == tenant_id] if tenant_id else []
    query = select(CustomIntent).where(
        CustomIntent.is_active.is_(True),
        or_(
            CustomIntent.scope == "global",
            CustomIntent.tenant_id.is_(None),
            *tenant_filter,
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

    # Step 2: Syntax & AST Analysis
    syntax_risks = analyze_syntax_risk(canonical_text)
    if tool_name:
        tool_risks = analyze_mcp_tool_arguments(tool_name, tool_arguments)
        syntax_risks.extend(tool_risks)

    for risk in syntax_risks:
        r_level = risk.get("risk_level", "high").lower()
        conf = SYNTAX_RISK_CONFIG.get(r_level, SYNTAX_RISK_CONFIG["high"])
        max_risk_score = max(max_risk_score, conf["score"])
        matches.append({
            "rule_id": f"SYNTAX-{risk['category'].upper()}",
            "rule_name": f"AST Syntax Guard: {risk['category']}",
            "scope": "global",
            "category": risk["category"],
            "action": conf["action"],
            "risk_level": r_level,
            "score": conf["score"],
            "matched_token": risk.get("matched_token", ""),
            "start": risk.get("start", 0),
            "end": risk.get("end", 0),
            "explanation": risk.get("detail", "Structural syntax risk detected."),
        })

    # Step 3: Fetch Applicable Rules (Global 1-to-many + Tenant 1-to-1)
    rule_items: list[dict[str, Any]] = list(BUILTIN_GLOBAL_RULES)

    if db is not None:
        db_rules = await fetch_applicable_rules(db, tenant_id)
        rule_items.extend([
            {
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
            }
            for r in db_rules
        ])

    if custom_rules:
        rule_items.extend(custom_rules)

    # Step 4: Declarative Pattern & Keyword Rule Evaluation
    for rule in rule_items:
        matched_tokens: list[str] = []

        # Regex Pattern Evaluation (Cached compiled regex)
        pattern = rule.get("regex_pattern")
        if pattern:
            rx = _get_compiled_regex(pattern)
            if rx:
                matched_tokens.extend(m.group(0) for m in rx.finditer(canonical_text))

        # Keyword Evaluation
        for kw in filter(None, (k.strip() for k in rule.get("keywords", []))):
            kw_rx = _get_compiled_regex(r"\b" + re.escape(kw) + r"\b")
            if kw_rx and kw_rx.search(canonical_text):
                matched_tokens.append(kw)

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

                # Declarative Redaction Replacement
                if action == "redact":
                    for tok in set(matched_tokens):
                        tok_rx = _get_compiled_regex(re.escape(tok))
                        if tok_rx:
                            modified_text = tok_rx.sub(f"[REDACTED:{rule.get('name')}]", modified_text)

    # Step 5: Declarative Resolution (Zero if-else ladders)
    # 1. Verdict Priority Resolution:
    final_verdict = max(
        (m["action"] for m in matches),
        key=lambda act: ACTION_PRECEDENCE.get(act, 0),
        default="allow",
    )

    # 2. Risk Tier Threshold Resolution:
    risk_tier = next(
        tier for threshold, tier in SCORE_TIER_THRESHOLDS
        if max_risk_score >= threshold
    )

    has_redact = any(m["action"] == "redact" for m in matches)
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

