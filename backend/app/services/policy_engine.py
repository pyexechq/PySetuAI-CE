import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.telemetry import current_trace_id, get_tracer
from app.schemas.openai import InspectionResult, PolicyViolation
from app.services.policy_bundle_service import get_tenant_default_bundle, load_bundle_rules
from app.services.injection_detection_service import scan_content

tracer = get_tracer(__name__)

SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
SECRET_PATTERN = re.compile(r"\b(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b")
INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(your\s+)?(system\s+)?prompt",
        r"(reveal|show|print|repeat|output|display)\s+(me\s+)?(your\s+)?(system\s+)?(prompt|instructions)",
        r"forget\s+(all\s+)?(your\s+)?(rules|instructions|guidelines)",
        r"bypass\s+(your\s+)?(restrictions|rules|guardrails|filters)",
        r"(developer|god|sudo|unrestricted|admin)\s+mode",
        r"jailbreak",
        r"you\s+are\s+now\s+dan",
    ]
]


@dataclass
class PolicyRuleDef:
    name: str
    action: str
    severity: str
    pattern: re.Pattern[str] | None = None
    keywords: list[str] | None = None


BUILTIN_RULES = [
    PolicyRuleDef("Detect SSN patterns", "Redact", "high", pattern=SSN_PATTERN),
    PolicyRuleDef(
        "Block system prompt override", "Block", "critical", keywords=["ignore previous", "disregard your prompt"]
    ),
    PolicyRuleDef("Secret key detection", "Block", "critical", pattern=SECRET_PATTERN),
    PolicyRuleDef("Prompt injection guard", "Block", "critical", pattern=INJECTION_PATTERNS[0]),
]

for extra in INJECTION_PATTERNS[1:]:
    BUILTIN_RULES.append(PolicyRuleDef("Prompt injection guard", "Block", "critical", pattern=extra))


def _condition_matches(
    condition: str,
    content: str,
    *,
    context: dict | None = None,
) -> tuple[bool, re.Pattern[str] | None]:
    cond = condition.strip()
    lower = content.lower()
    ctx = context or {}

    region_match = re.search(r"region\s*!=\s*['\"](\w+)['\"]", cond, re.IGNORECASE)
    if region_match:
        expected = region_match.group(1).upper()
        actual = str(ctx.get("region", "US")).upper()
        if re.search(r"\bhas_pii\b", cond, re.IGNORECASE):
            return actual != expected and bool(ctx.get("has_pii")), None
        return actual != expected, None

    if re.search(r"\bhas_pii\b", cond, re.IGNORECASE):
        has_pii = bool(ctx.get("has_pii"))
        if re.search(r"!\s*has_pii|\bnot\s+has_pii\b", cond, re.IGNORECASE):
            return not has_pii, None
        return has_pii, None

    contains_match = re.match(r"""prompt\.contains\(['"](.+?)['"]\)""", cond)
    if contains_match:
        needle = contains_match.group(1).lower()
        if needle == "ignore previous":
            return bool(re.search(r"ignore\s+(all\s+)?previous", lower)), None
        return needle in lower, None

    matches_match = re.match(r"content\.matches\(/(.+)/\)", cond)
    if matches_match:
        try:
            pattern = re.compile(matches_match.group(1))
            return pattern.search(content) is not None, pattern
        except re.error:
            return False, None

    if "ignore previous" in cond.lower():
        return "ignore previous" in lower, None
    if "jailbreak" in cond.lower():
        return "jailbreak" in lower, None
    if "you are now dan" in cond.lower():
        return "you are now dan" in lower, None

    return False, None


def _evaluate_rules(content: str, rules: list, *, context: dict | None = None) -> InspectionResult:
    violations: list[PolicyViolation] = []
    redacted = content
    blocked = False
    highest_risk = "low"
    risk_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    for raw in rules:
        if isinstance(raw, PolicyRuleDef):
            rule_name = raw.name
            action = raw.action
            severity = raw.severity
            matched = False
            detail = ""
            redact_pattern = raw.pattern

            if raw.pattern and raw.pattern.search(content):
                matched = True
                detail = f"Pattern matched: {rule_name}"
            elif raw.keywords:
                lower = content.lower()
                for kw in raw.keywords:
                    if kw in lower:
                        matched = True
                        detail = f"Keyword matched: {kw}"
                        break
        else:
            if not isinstance(raw, dict) or not raw.get("enabled", True):
                continue
            rule_name = str(raw.get("name", "Rule"))
            action = str(raw.get("action", "Allow"))
            severity = str(raw.get("severity", "medium"))
            condition = str(raw.get("condition", ""))
            matched, redact_pattern = _condition_matches(condition, content, context=context)
            policy_name = raw.get("policy_name")
            detail = f"Condition matched: {condition}" + (f" ({policy_name})" if policy_name else "")

        if not matched:
            continue

        violations.append(PolicyViolation(rule_name=rule_name, action=action, severity=severity, detail=detail))
        if risk_rank.get(severity, 0) > risk_rank.get(highest_risk, 0):
            highest_risk = severity
        if action == "Block":
            blocked = True
        elif action == "Redact":
            if isinstance(raw, PolicyRuleDef) and raw.pattern:
                redacted = raw.pattern.sub("[REDACTED]", redacted)
            elif isinstance(raw, dict):
                _, pattern = _condition_matches(str(raw.get("condition", "")), content, context=context)
                if pattern:
                    redacted = pattern.sub("[REDACTED]", redacted)
                elif SSN_PATTERN.search(content):
                    redacted = SSN_PATTERN.sub("[REDACTED]", redacted)

    if blocked:
        return InspectionResult(allowed=False, action="block", violations=violations, risk=highest_risk)
    if any(v.action == "Redact" for v in violations):
        return InspectionResult(
            allowed=True,
            action="redact",
            violations=violations,
            redacted_content=redacted,
            risk=highest_risk,
        )
    return InspectionResult(allowed=True, violations=violations, risk="low")


RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _merge_threat_scan(content: str, result: InspectionResult) -> InspectionResult:
    """Apply shared threat catalog on gateway ingress (covers bundle rule gaps)."""
    threat = scan_content(content)
    if not threat.detected or threat.recommended_action != "block":
        return result

    violations = list(result.violations)
    seen = {(v.rule_name, v.detail) for v in violations}
    for match in threat.matches:
        key = (match.name, match.detail)
        if key in seen:
            continue
        seen.add(key)
        violations.append(
            PolicyViolation(
                rule_name=match.name,
                action="Block",
                severity=match.severity,
                detail=match.detail,
            )
        )

    highest = max(
        [result.risk, threat.highest_severity],
        key=lambda level: RISK_RANK.get(level, 0),
    )
    return InspectionResult(allowed=False, action="block", violations=violations, risk=highest)


def inspect_content(content: str) -> InspectionResult:
    with tracer.start_as_current_span("policy.inspect") as span:
        span.set_attribute("helixguard.content_length", len(content))
        result = _evaluate_rules(content, BUILTIN_RULES)
        span.set_attribute("helixguard.inspection_action", result.action or "allow")
        span.set_attribute("helixguard.violation_count", len(result.violations))
        trace_id = current_trace_id()
        if trace_id:
            span.set_attribute("helixguard.trace_id", trace_id)
        return result


async def inspect_content_for_bundle(
    db: AsyncSession,
    tenant_id,
    bundle,
    content: str,
    *,
    context: dict | None = None,
) -> InspectionResult:
    stored_rules = await load_bundle_rules(db, tenant_id, bundle)
    if stored_rules:
        return _evaluate_rules(content, stored_rules, context=context)
    return inspect_content(content)


async def inspect_for_gateway(
    db: AsyncSession,
    tenant_id,
    bundle,
    content: str,
    *,
    context: dict | None = None,
) -> InspectionResult:
    if bundle is not None:
        result = await inspect_content_for_bundle(db, tenant_id, bundle, content, context=context)
    else:
        default_bundle = await get_tenant_default_bundle(db, tenant_id)
        if default_bundle is not None:
            result = await inspect_content_for_bundle(db, tenant_id, default_bundle, content, context=context)
        else:
            result = inspect_content(content)
    return _merge_threat_scan(content, result)
