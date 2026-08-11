from app.services.dashboard_metric_insights_service import METRIC_KEYS, METRIC_TITLES


def test_metric_catalog_covers_dashboard_cards() -> None:
    assert METRIC_TITLES["total_requests"] == "Total AI Requests"
    assert METRIC_TITLES["compliance_score"] == "Compliance Score"
    assert "protocol_translations" in METRIC_KEYS
