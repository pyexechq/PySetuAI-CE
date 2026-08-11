"""Open Policy Agent (OPA) integration for gateway ABAC decisions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import settings
from app.schemas.openai import ChatCompletionRequest, InspectionResult, PolicyViolation
from app.services.gateway_context import GatewayContext

logger = logging.getLogger(__name__)


@dataclass
class OpaViolation:
    rule: str
    message: str
    severity: str = "high"


@dataclass
class OpaDecision:
    allow: bool
    violations: list[OpaViolation] = field(default_factory=list)
    available: bool = True
    skipped: bool = False
    error: str | None = None


def build_gateway_opa_input(
    ctx: GatewayContext,
    request: ChatCompletionRequest,
    *,
    routed_model: str,
    has_pii: bool,
    region: str,
    risk: str,
    content_length: int,
    routing_context: dict | None = None,
) -> dict[str, Any]:
    role = ctx.user.role if ctx.user else "client_key"
    auth_type = "client_key" if ctx.client_api_key_id else "jwt"
    return {
        "subject": {
            "role": role,
            "actor": ctx.actor,
            "auth_type": auth_type,
        },
        "resource": {
            "bundle": ctx.policy_bundle_name or "",
            "tenant_id": str(ctx.tenant_id),
        },
        "request": {
            "model": request.model,
            "routed_model": routed_model,
        },
        "content": {
            "text_length": content_length,
            "has_pii": has_pii,
            "risk": risk,
        },
        "environment": {
            "region": region,
            "hour_utc": datetime.now(UTC).hour,
        },
        "routing_context": routing_context or request.routing_context or {},
    }


async def check_opa_health() -> tuple[bool, str | None]:
    if not settings.opa_enabled:
        return False, "OPA integration disabled"
    try:
        async with httpx.AsyncClient(timeout=settings.opa_timeout_seconds) as client:
            response = await client.get(f"{settings.opa_base_url.rstrip('/')}/health")
            if response.status_code == 200:
                return True, None
            return False, f"OPA health returned {response.status_code}"
    except httpx.HTTPError as exc:
        return False, str(exc)


async def evaluate_gateway_opa(input_payload: dict[str, Any]) -> OpaDecision:
    if not settings.opa_enabled:
        return OpaDecision(allow=True, skipped=True, available=False)

    url = f"{settings.opa_base_url.rstrip('/')}/v1/data/{settings.opa_policy_path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=settings.opa_timeout_seconds) as client:
            response = await client.post(url, json={"input": input_payload})
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        logger.warning("OPA evaluation failed: %s", exc)
        if settings.opa_fail_open:
            return OpaDecision(
                allow=True,
                available=False,
                skipped=True,
                error=str(exc),
            )
        return OpaDecision(
            allow=False,
            available=False,
            violations=[
                OpaViolation(
                    rule="OPA Unavailable",
                    message="Policy agent unreachable — request blocked (fail-closed)",
                    severity="critical",
                )
            ],
            error=str(exc),
        )

    result = body.get("result")
    if not isinstance(result, dict):
        decision = {"allow": True, "violations": []}
    elif "decision" in result and isinstance(result["decision"], dict):
        decision = result["decision"]
    else:
        decision = result

    raw_violations = decision.get("violations") or []
    violations: list[OpaViolation] = []
    if isinstance(raw_violations, list):
        for item in raw_violations:
            if isinstance(item, dict):
                violations.append(
                    OpaViolation(
                        rule=str(item.get("rule", "ABAC Rule")),
                        message=str(item.get("message", "ABAC policy violation")),
                        severity=str(item.get("severity", "high")),
                    )
                )

    allow = bool(decision.get("allow", len(violations) == 0))
    if violations:
        allow = False

    return OpaDecision(allow=allow, violations=violations, available=True)


def merge_opa_into_inspection(ingress: InspectionResult, opa: OpaDecision) -> InspectionResult:
    if opa.skipped or opa.allow:
        return ingress

    violations = list(ingress.violations)
    highest_risk = ingress.risk
    risk_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    for item in opa.violations:
        violations.append(
            PolicyViolation(
                rule_name=item.rule,
                action="Block",
                severity=item.severity,
                detail=f"OPA ABAC: {item.message}",
            )
        )
        if risk_rank.get(item.severity, 0) > risk_rank.get(highest_risk, 0):
            highest_risk = item.severity

    return InspectionResult(
        allowed=False,
        action="block",
        violations=violations,
        redacted_content=ingress.redacted_content,
        risk=highest_risk,
    )


async def evaluate_gateway_abac(
    ctx: GatewayContext,
    request: ChatCompletionRequest,
    ingress: InspectionResult,
    *,
    routed_model: str,
    has_pii: bool,
    region: str,
    content_length: int,
) -> tuple[InspectionResult, OpaDecision]:
    payload = build_gateway_opa_input(
        ctx,
        request,
        routed_model=routed_model,
        has_pii=has_pii,
        region=region,
        risk=ingress.risk,
        content_length=content_length,
    )
    opa = await evaluate_gateway_opa(payload)
    return merge_opa_into_inspection(ingress, opa), opa
