"""Tests for compliance live scoring helpers (BL-052)."""

from app.schemas.dashboard import DashboardComplianceControl
from app.services.compliance_service import (
    TenantComplianceSignals,
    _build_gdpr_controls,
    _build_hipaa_controls,
    _build_iso_controls,
    _build_nist_controls,
    _build_soc2_controls,
    _finalize_framework,
    _framework_status,
)
from app.services.compliance_snapshot_service import compute_period_compliance_metrics


def _signals(**overrides) -> TenantComplianceSignals:
    base = dict(
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
        request_log_retention_days=0,
        prompt_template_count=0,
    )
    base.update(overrides)
    return TenantComplianceSignals(**base)


def _by_id(controls, control_id: str) -> DashboardComplianceControl:
    return next(c for c in controls if c.id == control_id)


def test_compute_period_compliance_metrics_from_audit_counts() -> None:
    block_rate, score = compute_period_compliance_metrics(total_requests=200, blocked_requests=10)
    assert block_rate == 5.0
    assert score == 95.0


def test_compute_period_compliance_metrics_defaults_without_traffic() -> None:
    block_rate, score = compute_period_compliance_metrics(total_requests=0, blocked_requests=0)
    assert block_rate == 5.0
    assert score == 92.0


def test_framework_status_compliant_when_score_and_controls_pass() -> None:
    assert _framework_status(92.0, 10, 10) == "compliant"


def test_framework_status_partial_for_mid_scores() -> None:
    assert _framework_status(75.0, 7, 10) == "partial"


def test_framework_status_at_risk_when_low_score() -> None:
    assert _framework_status(55.0, 3, 10) == "at-risk"


def test_finalize_framework_weights_in_progress_controls() -> None:
    controls = [
        DashboardComplianceControl(
            id="c1",
            title="Control 1",
            requirement="Req",
            status="met",
        ),
        DashboardComplianceControl(
            id="c2",
            title="Control 2",
            requirement="Req",
            status="in_progress",
        ),
        DashboardComplianceControl(
            id="c3",
            title="Control 3",
            requirement="Req",
            status="not_met",
        ),
    ]
    framework = _finalize_framework("SOC 2 Type II", controls)
    assert framework.passed == 1
    assert framework.in_progress == 1
    assert framework.not_met == 1
    assert framework.score == 50.0
    assert framework.status == "at-risk"


def test_soc2_change_management_met_when_policies_are_active_without_drafts() -> None:
    control = _by_id(
        _build_soc2_controls(_signals(active_policy_names={"Data Exfiltration Block"})),
        "soc2-cc81",
    )
    assert control.status == "met"
    assert control.evidence
    assert "draft" not in (control.evidence or "").lower()


def test_gdpr_dpia_met_when_dlp_classification_is_active() -> None:
    control = _by_id(
        _build_gdpr_controls(_signals(active_policy_names={"DLP Classification"})),
        "gdpr-art35",
    )
    assert control.status == "met"
    assert "draft" not in (control.evidence or "").lower()


def test_not_met_controls_do_not_claim_supporting_evidence() -> None:
    control = _by_id(_build_iso_controls(_signals()), "iso-a122")
    assert control.status == "not_met"
    assert not control.evidence


def test_iso_abuse_protection_in_progress_does_not_claim_full_enforcement() -> None:
    control = _by_id(
        _build_iso_controls(_signals(active_policy_names={"Jailbreak Prevention"})),
        "iso-a122",
    )
    assert control.status == "in_progress"
    assert "enforced" not in (control.evidence or "").lower()


def test_hipaa_retention_met_when_request_log_retention_configured() -> None:
    control = _by_id(
        _build_hipaa_controls(_signals(request_log_retention_days=30)),
        "hipaa-retention",
    )
    assert control.status == "met"
    assert "30" in (control.evidence or "")


def test_gdpr_erasure_in_progress_when_retention_exists() -> None:
    control = _by_id(
        _build_gdpr_controls(_signals(request_log_retention_days=30)),
        "gdpr-art17",
    )
    assert control.status == "in_progress"
    assert control.evidence


def test_gdpr_transparency_can_be_met() -> None:
    control = _by_id(_build_gdpr_controls(_signals(audit_log_count=12)), "gdpr-transparency")
    assert control.status == "met"


def test_nist_toxicity_met_when_blocks_are_monitored() -> None:
    control = _by_id(
        _build_nist_controls(_signals(total_requests=100, blocked_requests=4, block_rate=4.0)),
        "nist-measure-2",
    )
    assert control.status == "met"


def test_iso_secure_development_met_when_prompt_templates_exist() -> None:
    control = _by_id(
        _build_iso_controls(_signals(prompt_template_count=3, active_policy_names={"Jailbreak Prevention"})),
        "iso-a141",
    )
    assert control.status == "met"
