"""Config-driven framework rule packs.

Rule packs are named, versioned collections of policy rules that can be attached
to a policy bundle. They are config-driven (not monolithic OPA), so a tenant can
opt into a compliance framework (OWASP, SOC2, HIPAA, GDPR, PCI-DSS) and get a
curated set of rules merged into their bundle evaluation without hand-writing
each rule.

Each rule uses the same dict shape as a stored policy rule:
``{id, name, condition, action, severity, enabled}``. Conditions use the
``content.matches(/pattern/flags)`` and ``content.contains('...')`` syntax
understood by ``policy_engine._condition_matches``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FrameworkRulePack:
    id: str
    name: str
    description: str
    version: str
    rules: list[dict] = field(default_factory=list)


FRAMEWORK_RULE_PACKS: dict[str, FrameworkRulePack] = {}


def _register(pack: FrameworkRulePack) -> None:
    FRAMEWORK_RULE_PACKS[pack.id] = pack


_register(
    FrameworkRulePack(
        id="owasp-llm-top10",
        name="OWASP LLM Top 10",
        description="Prompt injection, sensitive information disclosure, and insecure output handling guardrails.",
        version="1.0",
        rules=[
            {
                "id": "owasp-llm-01",
                "name": "Prompt injection guard",
                "condition": r"content.matches(/ignore\s+(all\s+)?previous\s+instructions/i)",
                "action": "Block",
                "severity": "critical",
                "enabled": True,
            },
            {
                "id": "owasp-llm-02",
                "name": "Jailbreak attempt",
                "condition": r"content.matches(/you\s+are\s+now\s+dan|do\s+anything\s+now/i)",
                "action": "Block",
                "severity": "critical",
                "enabled": True,
            },
            {
                "id": "owasp-llm-03",
                "name": "Sensitive information disclosure",
                "condition": r"content.matches(/\b(ssn|social\s+security\s+number|passport\s+number)\b/i)",
                "action": "Redact",
                "severity": "high",
                "enabled": True,
            },
            {
                "id": "owasp-llm-04",
                "name": "Insecure output handling",
                "condition": r"content.matches(/<script|javascript:|onerror=|onload=/)",
                "action": "Block",
                "severity": "high",
                "enabled": True,
            },
        ],
    )
)


_register(
    FrameworkRulePack(
        id="soc2",
        name="SOC 2",
        description="Security, availability, and confidentiality controls for service organizations.",
        version="1.0",
        rules=[
            {
                "id": "soc2-01",
                "name": "Credential exfiltration guard",
                "condition": r"content.matches(/(api[_-]?key|secret|password|token)\s*[:=]\s*\S+/i)",
                "action": "Block",
                "severity": "critical",
                "enabled": True,
            },
            {
                "id": "soc2-02",
                "name": "PII redaction",
                "condition": r"content.matches(/\b\d{3}-\d{2}-\d{4}\b|\b[\w.+-]+@[\w-]+\.[\w.]+\b/)",
                "action": "Redact",
                "severity": "high",
                "enabled": True,
            },
            {
                "id": "soc2-03",
                "name": "Availability disruption guard",
                "condition": r"content.matches(/(ddos|denial\s+of\s+service|crash\s+the\s+server)/i)",
                "action": "Block",
                "severity": "high",
                "enabled": True,
            },
        ],
    )
)


_register(
    FrameworkRulePack(
        id="hipaa",
        name="HIPAA",
        description="Protected health information (PHI) handling controls.",
        version="1.0",
        rules=[
            {
                "id": "hipaa-01",
                "name": "PHI redaction",
                "condition": r"content.matches(/\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b/)",
                "action": "Redact",
                "severity": "critical",
                "enabled": True,
            },
            {
                "id": "hipaa-02",
                "name": "Medical record disclosure guard",
                "condition": r"content.matches(/(medical\s+record|patient\s+name|diagnosis|treatment\s+plan)/i)",
                "action": "Redact",
                "severity": "high",
                "enabled": True,
            },
        ],
    )
)


_register(
    FrameworkRulePack(
        id="gdpr",
        name="GDPR",
        description="Personal data protection and data subject rights controls.",
        version="1.0",
        rules=[
            {
                "id": "gdpr-01",
                "name": "Personal data redaction",
                "condition": r"content.matches(/\b[\w.+-]+@[\w-]+\.[\w.]+\b|\b\d{3}-\d{2}-\d{4}\b/)",
                "action": "Redact",
                "severity": "high",
                "enabled": True,
            },
            {
                "id": "gdpr-02",
                "name": "Data subject request guard",
                "condition": r"content.matches(/(right\s+to\s+be\s+forgotten|data\s+erasure|data\s+portability)/i)",
                "action": "Alert",
                "severity": "medium",
                "enabled": True,
            },
        ],
    )
)


_register(
    FrameworkRulePack(
        id="pci-dss",
        name="PCI-DSS",
        description="Cardholder data protection controls.",
        version="1.0",
        rules=[
            {
                "id": "pci-01",
                "name": "Card number redaction",
                "condition": r"content.matches(/\b(?:\d[ -]?){13,16}\b/)",
                "action": "Redact",
                "severity": "critical",
                "enabled": True,
            },
            {
                "id": "pci-02",
                "name": "CVV disclosure guard",
                "condition": r"content.matches(/\b(cvv|cvc)\b\s*[:=]\s*\d{3,4}/i)",
                "action": "Block",
                "severity": "critical",
                "enabled": True,
            },
        ],
    )
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def list_framework_rule_packs() -> list[dict]:
    """Return the catalog as a list of pack summaries (without rules)."""
    return [
        {
            "id": pack.id,
            "name": pack.name,
            "description": pack.description,
            "version": pack.version,
            "rule_count": len(pack.rules),
        }
        for pack in FRAMEWORK_RULE_PACKS.values()
    ]


def get_framework_rule_pack(pack_id: str) -> FrameworkRulePack | None:
    return FRAMEWORK_RULE_PACKS.get(pack_id)


def resolve_framework_rules(pack_ids: list[str]) -> list[dict]:
    """Return the merged rules for the given pack ids, in catalog order."""
    merged: list[dict] = []
    for pack_id in pack_ids:
        pack = FRAMEWORK_RULE_PACKS.get(pack_id)
        if pack is None:
            continue
        for rule in pack.rules:
            merged.append({**rule, "policy_name": f"Framework: {pack.name}"})
    return merged
