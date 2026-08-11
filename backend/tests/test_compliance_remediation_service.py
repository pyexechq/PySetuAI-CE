from app.services.compliance_remediation_service import (
    build_framework_gap_summary,
    find_control,
    framework_slug,
    resolve_framework_name,
    _manual_steps,
    _template_ai_steps,
)
from app.schemas.dashboard import DashboardComplianceControl, DashboardComplianceFramework


def _sample_framework() -> DashboardComplianceFramework:
    controls = [
        DashboardComplianceControl(
            id="gdpr-art25",
            title="Art. 25 — Data protection by design",
            requirement="Embed privacy controls",
            status="not_met",
            remediation="Activate PII Redaction policies in Policy Studio.",
            helixguard_module="Policy Studio",
        ),
        DashboardComplianceControl(
            id="gdpr-art30",
            title="Art. 30 — Records of processing",
            requirement="Maintain auditable records",
            status="met",
            evidence="42 audit events captured",
            helixguard_module="Audit Explorer",
        ),
    ]
    return DashboardComplianceFramework(
        name="GDPR",
        score=69.0,
        status="at-risk",
        controls=2,
        passed=1,
        in_progress=0,
        not_met=1,
        control_items=controls,
    )


def test_resolve_framework_slug() -> None:
    assert resolve_framework_name("gdpr") == "GDPR"
    assert framework_slug("GDPR") == "gdpr"


def test_manual_steps_include_module_route_hint() -> None:
    framework = _sample_framework()
    control = find_control(framework, "gdpr-art25")
    steps = _manual_steps(control)
    assert any("Policy Studio" in step for step in steps)
    assert any("re-evaluate" in step.lower() for step in steps)


def test_template_ai_steps_when_no_llm() -> None:
    framework = _sample_framework()
    control = find_control(framework, "gdpr-art25")
    steps = _template_ai_steps(control, framework)
    assert len(steps) >= 4


def test_gap_summary_counts() -> None:
    summary = build_framework_gap_summary(_sample_framework())
    assert summary["gaps_count"] == 1
    assert summary["not_met"] == 1
    assert summary["priority_controls"][0]["id"] == "gdpr-art25"
