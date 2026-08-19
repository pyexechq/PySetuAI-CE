from app.models.governance import AlertWebhook
from app.schemas.incident import SecurityIncidentEvent
from app.services.alert_webhook_service import build_servicenow_payload
from app.services.incident_adapters.webhook import GenericWebhookAdapter


def test_build_servicenow_payload_uses_config() -> None:
    payload = build_servicenow_payload(
        {
            "action": "gateway.policy.block",
            "resource": "gpt-4",
            "risk": "critical",
            "details": "blocked",
            "trace_id": "trace-1",
        },
        {"assignment_group": "SecOps", "category": "AI"},
    )
    assert payload["urgency"] == "1"
    assert payload["assignment_group"] == "SecOps"
    assert payload["category"] == "AI"
    assert payload["correlation_id"] == "trace-1"


def test_generic_webhook_envelope_create() -> None:
    from app.services.incident_adapters.webhook import _envelope

    event = SecurityIncidentEvent(
        event_id="e1",
        tenant_id="t1",
        source="gateway",
        action="gateway.policy.block",
        title="Blocked",
        actor="user@acme.com",
        resource="gpt-4",
        status="blocked",
        risk="high",
        details="x",
        occurred_at="2026-08-15T00:00:00Z",
    )
    envelope = _envelope("create", event, {"key": "val"})
    assert envelope["action"] == "create"
    assert envelope["event"]["action"] == "gateway.policy.block"
    assert envelope["connector_config"]["key"] == "val"


def test_generic_webhook_envelope_update() -> None:
    from app.services.incident_adapters.webhook import _envelope

    event = SecurityIncidentEvent(
        event_id="e1",
        tenant_id="t1",
        source="gateway",
        action="gateway.policy.block",
        title="Blocked",
        actor="user@acme.com",
        resource="gpt-4",
        status="blocked",
        risk="high",
        details="x",
        occurred_at="2026-08-15T00:00:00Z",
    )
    envelope = _envelope("update", event, None, ticket_id="INC-9")
    assert envelope["action"] == "update"
    assert envelope["ticket_id"] == "INC-9"


def test_datadog_event_payload_create() -> None:
    from app.services.incident_adapters.datadog import _build_event_payload

    connector = AlertWebhook(
        name="Datadog",
        webhook_type="datadog",
        endpoint_url="https://api.datadoghq.com",
        config_json={"service": "pysetu-gateway", "source_type_name": "pysetu", "tags": ["env:prod"]},
    )
    event = SecurityIncidentEvent(
        event_id="e1",
        tenant_id="t1",
        tenant_slug="acme",
        source="gateway",
        action="gateway.policy.block",
        title="Blocked",
        actor="user@acme.com",
        resource="gpt-4",
        status="blocked",
        risk="critical",
        details="policy violation",
        occurred_at="2026-08-15T00:00:00Z",
        fingerprint="fp-1",
    )
    payload = _build_event_payload(connector, event, aggregation_key=event.fingerprint)
    assert payload["alert_type"] == "error"
    assert payload["aggregation_key"] == "fp-1"
    assert payload["service"] == "pysetu-gateway"
    assert "tenant:acme" in payload["tags"]
    assert "risk:critical" in payload["tags"]
    assert "env:prod" in payload["tags"]


def test_datadog_event_payload_update_is_followup() -> None:
    from app.services.incident_adapters.datadog import _build_event_payload

    connector = AlertWebhook(name="Datadog", webhook_type="datadog", endpoint_url="https://api.datadoghq.com")
    event = SecurityIncidentEvent(
        event_id="e1",
        tenant_id="t1",
        source="gateway",
        action="gateway.policy.block",
        title="Blocked",
        actor="user@acme.com",
        resource="gpt-4",
        status="blocked",
        risk="high",
        details="x",
        occurred_at="2026-08-15T00:00:00Z",
    )
    payload = _build_event_payload(connector, event, aggregation_key="12345", is_followup=True)
    assert payload["aggregation_key"] == "12345"
    assert payload["title"].startswith("PySetu duplicate occurrence:")


def test_datadog_events_url_appends_path() -> None:
    from app.services.incident_adapters.datadog import _events_url

    assert _events_url("https://api.datadoghq.com") == "https://api.datadoghq.com/api/v1/events"
    assert _events_url("https://api.datadoghq.eu/api/v1/events") == "https://api.datadoghq.eu/api/v1/events"
