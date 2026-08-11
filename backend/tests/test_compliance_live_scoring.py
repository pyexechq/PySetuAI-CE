"""Tests for compliance live scoring helpers (BL-052)."""

from app.schemas.dashboard import DashboardComplianceControl
from app.services.compliance_service import _finalize_framework, _framework_status
from app.services.compliance_snapshot_service import compute_period_compliance_metrics


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
