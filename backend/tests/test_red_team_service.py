from app.services.red_team_service import campaign_csv, run_campaign


def test_red_team_baseline_detects_attacks_and_allows_control() -> None:
    report = run_campaign()

    assert report.total_cases == 6
    assert report.failed_cases == 0
    assert report.overall_status == "pass"
    assert report.detection_rate == 100.0
    assert any(result.category == "benign_control" and not result.detected for result in report.results)


def test_red_team_report_exports_case_results() -> None:
    report = run_campaign()
    exported = campaign_csv(report)

    assert "case_id,category,name" in exported
    assert "RT-003" in exported
    assert "data_exfiltration" in exported