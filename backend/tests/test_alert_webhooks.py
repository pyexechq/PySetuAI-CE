from unittest.mock import AsyncMock, patch
import asyncio
import uuid

from app.services.alert_webhook_service import (
    build_gateway_alert_event,
    build_servicenow_payload,
    build_slack_payload,
    dispatch_tenant_alerts,
    gateway_block_action,
)


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
    assert payload["short_description"].startswith("PySetu:")


def test_build_gateway_alert_event_includes_trace_and_tenant() -> None:
    event = build_gateway_alert_event(
        action="gateway.policy.block",
        actor="user@acme.com",
        resource="gpt-4 /chat",
        status="blocked",
        risk="high",
        details="PII detected",
        tenant="acme",
        trace_id="trace-123",
    )
    assert event["action"] == "gateway.policy.block"
    assert event["tenant"] == "acme"
    assert event["trace_id"] == "trace-123"
    assert "blocked" in event["title"].lower()


def test_gateway_block_action_maps_audit_actions() -> None:
    assert gateway_block_action("LLM Request", injection=True) == "gateway.injection.block"
    assert gateway_block_action("ABAC Policy") == "gateway.abac.block"
    assert gateway_block_action("LLM Response") == "gateway.egress.block"
    assert gateway_block_action("LLM Request") == "gateway.policy.block"


def test_dispatch_tenant_alerts_delivers_to_enabled_webhooks() -> None:
    tenant_id = uuid.uuid4()
    webhook = type(
        "Webhook",
        (),
        {
            "id": uuid.uuid4(),
            "name": "Slack Ops",
            "webhook_type": "slack",
            "enabled": True,
            "alerts_sent": 0,
            "last_alert_at": None,
            "last_error": "",
        },
    )()

    db = AsyncMock()
    event = build_gateway_alert_event(
        action="gateway.policy.block",
        actor="user@acme.com",
        resource="gpt-4 /chat",
        status="blocked",
        risk="high",
        details="Blocked",
    )

    async def run() -> None:
        with patch(
            "app.services.alert_webhook_service.list_webhooks",
            AsyncMock(return_value=[webhook]),
        ), patch(
            "app.services.alert_webhook_service.send_alert",
            AsyncMock(),
        ) as send_alert:
            results = await dispatch_tenant_alerts(db, tenant_id, event)

        send_alert.assert_awaited_once_with(webhook, event)
        assert len(results) == 1
        assert results[0].delivered is True
        assert webhook.alerts_sent == 1
        db.commit.assert_awaited()

    asyncio.run(run())


def test_dispatch_tenant_alerts_records_failure_without_raising() -> None:
    tenant_id = uuid.uuid4()
    webhook = type(
        "Webhook",
        (),
        {
            "id": uuid.uuid4(),
            "name": "ServiceNow",
            "webhook_type": "servicenow",
            "enabled": True,
            "alerts_sent": 2,
            "last_alert_at": None,
            "last_error": "",
        },
    )()
    db = AsyncMock()

    async def run() -> None:
        with patch(
            "app.services.alert_webhook_service.list_webhooks",
            AsyncMock(return_value=[webhook]),
        ), patch(
            "app.services.alert_webhook_service.send_alert",
            AsyncMock(side_effect=Exception("network down")),
        ):
            results = await dispatch_tenant_alerts(db, tenant_id, {"action": "gateway.policy.block"})

        assert len(results) == 1
        assert results[0].delivered is False
        assert "network down" in results[0].message
        assert webhook.last_error == "network down"

    asyncio.run(run())
