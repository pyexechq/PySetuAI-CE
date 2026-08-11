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
    "Compliance Center": "/compliance",
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


def _manual_steps(control: DashboardComplianceControl) -> list[str]:
    steps: list[str] = []
    if control.remediation:
        steps.append(control.remediation)
    if control.pysetu_module:
        route = MODULE_ROUTES.get(control.pysetu_module, "/")
        steps.append(
            f"Navigate to {control.pysetu_module} ({route}) and apply the configuration described above."
        )
    if control.status == "not_met":
        steps.append("Validate evidence appears under the control (status should move to In progress or Met).")
    elif control.status == "in_progress":
        steps.append("Complete remaining configuration and confirm evidence is captured in Audit Explorer or Reports.")
    steps.append(f"Return to Compliance Center and re-evaluate {control.title}.")
    return steps


def _template_ai_steps(control: DashboardComplianceControl, framework: DashboardComplianceFramework) -> list[str]:
    """Deterministic expanded plan when live LLM is unavailable."""
    base = _manual_steps(control)
    prefix = [
        f"Framework: {framework.name} · Control: {control.title}",
        f"Gap: control is currently '{control.status.replace('_', ' ')}'.",
        "Recommended execution order:",
    ]
    numbered = [f"{index + 1}. {step}" for index, step in enumerate(base)]
    suffix = [
        "Assign an owner and target date in your GRC tracker.",
        "Attach exported evidence from Reports or a Compliance snapshot after verification.",
    ]
    return prefix + numbered + suffix


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
    manual_route = MODULE_ROUTES.get(control.pysetu_module or "")
    effort = "Low" if control.status == "in_progress" else "Medium" if control.status == "not_met" else "Low"

    if mode == "manual":
        steps = _manual_steps(control)
        return {
            "control_id": control.id,
            "framework_name": framework.name,
            "framework_slug": framework_slug(framework.name),
            "mode": "manual",
            "summary": control.remediation or f"Manual remediation for {control.title}.",
            "steps": steps,
            "manual_route": manual_route or None,
            "ai_generated": False,
            "estimated_effort": effort,
            "generated_at": datetime.now(UTC),
        }

    if mode != "ai":
        raise ValueError("mode must be 'manual' or 'ai'")

    ai_config = await resolve_ai_assist_config(db, tenant_id)
    prompt = (
        "You are a GRC engineer helping remediate PySetu AI compliance gaps. "
        "Return ONLY a JSON array of 4-6 short imperative steps (strings), no markdown.\n\n"
        f"Framework: {framework.name}\n"
        f"Control: {control.title}\n"
        f"Status: {control.status}\n"
        f"Requirement: {control.requirement}\n"
        f"PySetu module: {control.pysetu_module or 'N/A'}\n"
        f"Known remediation hint: {control.remediation or 'None'}\n"
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
        "manual_route": manual_route or None,
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
