"""Compliance re-evaluation and remediation planning for the Compliance Center."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.dashboard import DashboardComplianceControl, DashboardComplianceFramework
from app.services.ai_assist_config_service import complete_ai_assist, resolve_ai_assist_config
from app.services.compliance_snapshot_service import load_live_frameworks
from app.schemas.openai import ChatMessage

FRAMEWORK_SLUGS: dict[str, str] = {
    "gdpr": "GDPR",
    "hipaa": "HIPAA",
    "soc2": "SOC 2 Type II",
    "iso27001": "ISO 27001",
    "nist-ai-rmf": "NIST AI RMF",
}

MODULE_ROUTES: dict[str, str] = {
    "Policy Studio": "/policy-studio",
    "Audit Explorer": "/audit-explorer",
    "Security Center": "/monitoring?tab=security",
    "Observability": "/monitoring?tab=traces",
    "Monitoring": "/monitoring",
    "LLM Router": "/llm-router",
    "MCP Governance": "/mcp-governance",
    "Governance Sandbox": "/studio",
    "Compatibility Center": "/compatibility-center",
    "Reports": "/reports",
    "Data Protection": "/data-protection",
    "Settings": "/settings/organization",
    "Policy Bundles": "/settings/policy-bundles",
    "Users & RBAC": "/settings/users",
    "Integrations": "/settings/integrations",
    "Prompt templates": "/settings/prompts",
    "Client API keys": "/settings/api-keys",
    "Compliance Center": "/compliance",
    "Studio": "/studio",
    "Governance Graph": "/governance-graph",
}

CONTROL_ROUTES: dict[str, str] = {
    "gdpr-art17": "/audit-explorer?tab=integrations",
    "gdpr-art30": "/settings/api-keys",
    "gdpr-art33": "/monitoring?tab=security",
    "gdpr-art35": "/compliance?tab=evidence",
    "gdpr-transparency": "/audit-explorer",
    "hipaa-164308": "/settings/users",
    "hipaa-164314": "/settings/integrations",
    "hipaa-audit": "/settings/api-keys",
    "hipaa-incident": "/monitoring?tab=security",
    "hipaa-retention": "/audit-explorer?tab=integrations",
    "soc2-cc61": "/settings/users",
    "soc2-cc72": "/monitoring",
    "soc2-incident": "/monitoring?tab=security",
    "iso-a91": "/settings/users",
    "iso-a124": "/settings/api-keys",
    "iso-a141": "/settings/prompts",
    "iso-a181": "/compliance?tab=evidence",
    "iso-a161": "/monitoring?tab=security",
    "nist-measure-1": "/monitoring",
    "nist-map-2": "/reports",
}


def framework_slug(name: str) -> str:
    for slug, label in FRAMEWORK_SLUGS.items():
        if label == name:
            return slug
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def resolve_framework_name(slug_or_name: str) -> str | None:
    key = slug_or_name.strip().lower()
    if key in FRAMEWORK_SLUGS:
        return FRAMEWORK_SLUGS[key]
    for label in FRAMEWORK_SLUGS.values():
        if label.lower() == key or label.lower().replace(" ", "-") == key:
            return label
    return None


async def reevaluate_framework(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    slug_or_name: str,
) -> tuple[DashboardComplianceFramework, datetime]:
    name = resolve_framework_name(slug_or_name)
    if name is None:
        raise ValueError(f"Unknown framework '{slug_or_name}'")

    frameworks = await load_live_frameworks(db, tenant_id)
    framework = next((f for f in frameworks if f.name == name), None)
    if framework is None:
        raise ValueError(f"Framework '{name}' not found")

    return framework, datetime.now(UTC)


def find_control(framework: DashboardComplianceFramework, control_id: str) -> DashboardComplianceControl:
    for control in framework.control_items:
        if control.id == control_id:
            return control
    raise ValueError(f"Control '{control_id}' not found in {framework.name}")


def _module_route(control: DashboardComplianceControl) -> str | None:
    return CONTROL_ROUTES.get(control.id) or MODULE_ROUTES.get(control.pysetu_module or "") or None


def _manual_steps(control: DashboardComplianceControl) -> list[str]:
    steps: list[str] = []
    if control.remediation:
        steps.append(control.remediation)
    if control.status == "not_met":
        steps.append("After the change, re-evaluate this framework so the control can move to In progress or Met.")
    elif control.status == "in_progress":
        steps.append("Finish any remaining operator work, then re-evaluate this framework to refresh evidence.")
    else:
        steps.append(f"Re-evaluate {control.title} in Compliance Center if you need a fresh score.")
    return steps


def _template_ai_steps(control: DashboardComplianceControl, _framework: DashboardComplianceFramework) -> list[str]:
    """Deterministic plan when live LLM is unavailable."""
    route = _module_route(control) or "/"
    module = control.pysetu_module or "Compliance Center"
    steps = _manual_steps(control)
    steps.insert(1, f"Open {module} at {route} and complete the action in the product — do not use a different Settings page.")
    return steps


def _parse_ai_steps(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        payload = json.loads(stripped)
        if isinstance(payload, list):
            return [str(item).strip() for item in payload if str(item).strip()]
        if isinstance(payload, dict) and isinstance(payload.get("steps"), list):
            return [str(item).strip() for item in payload["steps"] if str(item).strip()]
    except json.JSONDecodeError:
        pass

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    steps: list[str] = []
    for line in lines:
        cleaned = re.sub(r"^[\d\.\)\-\*]+\s*", "", line)
        if cleaned:
            steps.append(cleaned)
    return steps[:8]


async def build_remediation_plan(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    framework: DashboardComplianceFramework,
    control: DashboardComplianceControl,
    mode: str,
) -> dict:
    manual_route = _module_route(control)
    effort = "Low" if control.status == "in_progress" else "Medium" if control.status == "not_met" else "Low"

    if mode == "manual":
        steps = _manual_steps(control)
        summary = control.evidence or control.remediation or f"Manual remediation for {control.title}."
        return {
            "control_id": control.id,
            "framework_name": framework.name,
            "framework_slug": framework_slug(framework.name),
            "mode": "manual",
            "summary": summary,
            "steps": steps,
            "manual_route": manual_route,
            "module_name": control.pysetu_module,
            "evidence": control.evidence,
            "ai_generated": False,
            "estimated_effort": effort,
            "generated_at": datetime.now(UTC),
        }

    if mode != "ai":
        raise ValueError("mode must be 'manual' or 'ai'")

    ai_config = await resolve_ai_assist_config(db, tenant_id)
    prompt = (
        "You are a GRC engineer helping remediate a PySetu AI compliance gap. "
        "Return ONLY a JSON array of 4-6 short imperative steps (strings), no markdown.\n"
        "Use only the PySetu screen and URL provided. Do not send the user to Organization settings "
        "unless that URL is explicitly given. Do not invent DSAR consoles, BAA upload forms, or worksheets "
        "that are not named below.\n\n"
        f"Framework: {framework.name}\n"
        f"Control: {control.title}\n"
        f"Status: {control.status}\n"
        f"Requirement: {control.requirement}\n"
        f"PySetu screen: {control.pysetu_module or 'Compliance Center'}\n"
        f"URL: {_module_route(control) or '/compliance'}\n"
        f"Known remediation: {control.remediation or 'None'}\n"
        f"Evidence today: {control.evidence or 'None'}"
    )

    ai_generated = False
    steps: list[str] = []
    summary = f"AI remediation plan for {control.title} under {framework.name}."

    text, ok = await complete_ai_assist(ai_config, [ChatMessage(role="user", content=prompt)], temperature=0.3)
    if ok and text:
        parsed = _parse_ai_steps(text)
        if parsed:
            steps = parsed
            ai_generated = True
            summary = f"AI-generated remediation plan for {control.title}."

    if not steps:
        steps = _template_ai_steps(control, framework)
        summary = f"Structured remediation plan for {control.title} (AI Assist unavailable — using PySetu playbook)."

    return {
        "control_id": control.id,
        "framework_name": framework.name,
        "framework_slug": framework_slug(framework.name),
        "mode": "ai",
        "summary": summary,
        "steps": steps,
        "manual_route": manual_route,
        "module_name": control.pysetu_module,
        "evidence": control.evidence,
        "ai_generated": ai_generated,
        "estimated_effort": effort,
        "generated_at": datetime.now(UTC),
    }


def build_framework_gap_summary(framework: DashboardComplianceFramework) -> dict:
    gaps = [c for c in framework.control_items if c.status != "met"]
    return {
        "framework_name": framework.name,
        "framework_slug": framework_slug(framework.name),
        "gaps_count": len(gaps),
        "not_met": sum(1 for c in gaps if c.status == "not_met"),
        "in_progress": sum(1 for c in gaps if c.status == "in_progress"),
        "priority_controls": [
            {
                "id": c.id,
                "title": c.title,
                "status": c.status,
                "pysetu_module": c.pysetu_module,
            }
            for c in gaps
            if c.status == "not_met"
        ][:5],
    }
