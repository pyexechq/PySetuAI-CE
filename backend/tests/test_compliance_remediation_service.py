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
            pysetu_module="Policy Studio",
        ),
        DashboardComplianceControl(
            id="gdpr-art30",
            title="Art. 30 — Records of processing",
            requirement="Maintain auditable records",
            status="met",
            evidence="42 audit events captured",
            pysetu_module="Audit Explorer",
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
    assert control.remediation in steps
    assert any("re-evaluate" in step.lower() for step in steps)
    assert steps.count(control.remediation) == 1


def test_every_control_module_has_a_known_route() -> None:
    from app.services.compliance_remediation_service import MODULE_ROUTES, _module_route
    from app.services.compliance_service import (
        TenantComplianceSignals,
        _build_gdpr_controls,
        _build_hipaa_controls,
        _build_iso_controls,
        _build_nist_controls,
        _build_soc2_controls,
    )

    signals = TenantComplianceSignals(
        active_policy_names=set(),
        draft_policy_count=0,
        audit_log_count=0,
        pii_events=0,
        blocked_requests=0,
        total_requests=0,
        mcp_server_count=0,
        high_risk_mcp_count=0,
        llm_provider_count=0,
        compliance_score=0.0,
        block_rate=0.0,
        request_log_retention_days=30,
        prompt_template_count=0,
    )
    controls = (
        _build_gdpr_controls(signals)
        + _build_hipaa_controls(signals)
        + _build_soc2_controls(signals)
        + _build_iso_controls(signals)
        + _build_nist_controls(signals)
    )
    forbidden_org_settings = {
        "gdpr-art17",
        "hipaa-164308",
        "hipaa-164314",
        "hipaa-retention",
        "soc2-cc61",
        "iso-a91",
    }
    for control in controls:
        assert control.pysetu_module, f"{control.id} missing module"
        assert control.pysetu_module in MODULE_ROUTES, f"{control.id} unknown module {control.pysetu_module}"
        route = _module_route(control)
        assert route and route.startswith("/"), f"{control.id} missing route"
        if control.id in forbidden_org_settings:
            assert route != "/settings/organization", f"{control.id} still points at Organization settings"
        steps = _manual_steps(control)
        assert len(steps) == len(set(steps)), f"{control.id} has duplicate steps"


def test_template_ai_steps_are_actionable() -> None:
    framework = _sample_framework()
    control = find_control(framework, "gdpr-art25")
    steps = _template_ai_steps(control, framework)
    assert steps
    assert not any("recommended execution order" in step.lower() for step in steps)


def test_art17_remediation_points_to_audit_explorer_retention() -> None:
    from app.services.compliance_remediation_service import _module_route
    from app.services.compliance_service import TenantComplianceSignals, _build_gdpr_controls

    signals = TenantComplianceSignals(
        active_policy_names=set(),
        draft_policy_count=0,
        audit_log_count=0,
        pii_events=0,
        blocked_requests=0,
        total_requests=0,
        mcp_server_count=0,
        high_risk_mcp_count=0,
        llm_provider_count=0,
        compliance_score=0.0,
        block_rate=0.0,
        request_log_retention_days=30,
    )
    control = next(c for c in _build_gdpr_controls(signals) if c.id == "gdpr-art17")
    assert control.pysetu_module == "Audit Explorer"
    assert _module_route(control) == "/audit-explorer?tab=integrations"
    joined = " ".join(_manual_steps(control)).lower()
    assert "/settings/organization" not in joined
    assert "erasure runbook and link retention policies" not in joined


def test_template_ai_steps_when_no_llm() -> None:
    framework = _sample_framework()
    control = find_control(framework, "gdpr-art25")
    steps = _template_ai_steps(control, framework)
    assert len(steps) >= 2


def test_gap_summary_counts() -> None:
    summary = build_framework_gap_summary(_sample_framework())
    assert summary["gaps_count"] == 1
    assert summary["not_met"] == 1
    assert summary["priority_controls"][0]["id"] == "gdpr-art25"
