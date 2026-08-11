from app.services.alert_webhook_service import build_servicenow_payload, build_slack_payload


def test_build_slack_payload_includes_blocks_and_risk() -> None:
    payload = build_slack_payload(
        {
            "title": "Policy blocked",
            "action": "policy.violation",
            "actor": "user@acme.com",
            "resource": "gpt-4",
            "status": "blocked",
            "risk": "high",
            "details": "PII detected in prompt",
        },
        channel="#security",
    )
    assert payload["channel"] == "#security"
    assert "blocks" in payload
    assert "policy.violation" in payload["text"]
    assert any("PII detected" in str(block) for block in payload["blocks"])


def test_build_servicenow_payload_maps_urgency_by_risk() -> None:
    payload = build_servicenow_payload(
        {
            "action": "gateway.block",
            "resource": "claude-3",
            "risk": "critical",
            "details": "Cross-region data transfer blocked",
        }
    )
    assert payload["urgency"] == "1"
    assert payload["category"] == "Security"
    assert "Cross-region" in payload["description"]
    assert payload["short_description"].startswith("HelixGuard:")
