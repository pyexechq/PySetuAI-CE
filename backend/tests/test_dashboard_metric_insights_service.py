from app.schemas.auth import DashboardMetricsResponse
from app.schemas.dashboard import (
    DashboardComplianceFramework,
    DashboardMetricInsightResponse,
    DashboardOverviewResponse,
    MetricInsightContextRequest,
)
from app.services.dashboard_metric_insights_service import (
    METRIC_KEYS,
    METRIC_TITLES,
    _apply_card_context,
    _metric_snapshot,
    _playbook_insight,
)


def test_metric_catalog_covers_dashboard_cards() -> None:
    assert METRIC_TITLES["total_requests"] == "Total AI Requests"
    assert METRIC_TITLES["compliance_score"] == "Compliance Score"
    assert "protocol_translations" in METRIC_KEYS


def _overview_with_frameworks() -> DashboardOverviewResponse:
    metrics = DashboardMetricsResponse(
        total_requests=100,
        blocked_requests=8,
        pii_redactions=2,
        policy_violations=8,
        mcp_violations=0,
        cost_savings=0.0,
        compliance_score=70.0,
        success_rate=92.0,
    )
    return DashboardOverviewResponse(
        metrics=metrics,
        traffic=[],
        risk_distribution=[],
        top_threats=[],
        llm_usage=[],
        mcp_activity=[],
        top_policies=[],
        top_agents=[],
        compliance_frameworks=[
            DashboardComplianceFramework(
                name="GDPR",
                score=80.0,
                status="partial",
                controls=10,
                passed=8,
                in_progress=0,
                not_met=2,
            ),
            DashboardComplianceFramework(
                name="HIPAA",
                score=60.0,
                status="at-risk",
                controls=10,
                passed=6,
                in_progress=0,
                not_met=4,
            ),
        ],
        security_trends=[],
    )


def test_compliance_score_insight_uses_framework_average() -> None:
    overview = _overview_with_frameworks()
    insight = _playbook_insight("compliance_score", overview)
    assert "70%" in insight.summary
    assert "block rate" not in insight.summary.lower()
    joined = " ".join(insight.insights)
    assert "HIPAA" in joined
    assert "Compliance Center" in joined

    snapshot = _metric_snapshot("compliance_score", overview)
    assert snapshot["value"] == 70.0
    assert snapshot["source"] == "average of live framework control scores"
    assert [row["name"] for row in snapshot["frameworks"]] == ["GDPR", "HIPAA"]


def test_card_context_overrides_summary_and_title() -> None:
    overview = _overview_with_frameworks()
    base = _playbook_insight("blocked_requests", overview)
    context = MetricInsightContextRequest(
        card_title="Block rate",
        display_value="4.2%",
        period_label="selected range",
    )
    adjusted = _apply_card_context("blocked_requests", overview, base, context)
    assert adjusted.title == "Block rate"
    assert adjusted.summary == "Block rate is 4.2% (selected range)."
    assert any("baseline" in item.lower() for item in adjusted.insights)


def test_card_context_keeps_matching_dashboard_value_without_baseline_note() -> None:
    overview = _overview_with_frameworks()
    base = _playbook_insight("compliance_score", overview)
    context = MetricInsightContextRequest(
        card_title="Compliance Score",
        display_value="70%",
    )
    adjusted = _apply_card_context("compliance_score", overview, base, context)
    assert adjusted.summary == "Compliance Score is 70%."
    assert not any("baseline" in item.lower() for item in adjusted.insights)
