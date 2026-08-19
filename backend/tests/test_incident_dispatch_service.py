import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.incident import SecurityIncidentEvent, compute_incident_fingerprint
from app.services.incident_event_builder import (
    build_security_incident_event_from_audit,
    map_audit_source,
)
from app.models.governance import AuditLog


def test_fingerprint_stable_for_same_inputs() -> None:
    e1 = SecurityIncidentEvent(
        event_id="a",
        tenant_id="t1",
        tenant_slug="acme",
        source="gateway",
        action="gateway.policy.block",
        title="Blocked",
        actor="user@acme.com",
        resource="gpt-4",
        status="blocked",
        risk="high",
        details="x",
        occurred_at="2026-08-15T00:00:00Z",
        policy_bundle="standard",
        matched_rule="pii",
    )
    e2 = e1.model_copy()
    assert compute_incident_fingerprint(e1) == compute_incident_fingerprint(e2)


def test_fingerprint_changes_when_actor_changes() -> None:
    base = SecurityIncidentEvent(
        event_id="a",
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
    other = base.model_copy(update={"actor": "other@acme.com"})
    assert compute_incident_fingerprint(base) != compute_incident_fingerprint(other)


def test_build_from_gateway_blocked_audit() -> None:
    tenant_id = uuid.uuid4()
    log = AuditLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        timestamp=datetime.now(UTC),
        actor="user@acme.com",
        action="LLM Request",
        resource="gpt-4 /chat",
        status="blocked",
        risk="high",
        details="trace_id=abc; PII detected",
    )
    event = build_security_incident_event_from_audit(log, tenant_slug="acme")
    assert event.source == "gateway"
    assert event.risk == "high"
    assert event.action == "gateway.policy.block"
    assert event.trace_id == "abc"
    assert event.fingerprint


def test_map_rag_audit_source() -> None:
    log = AuditLog(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        timestamp=datetime.now(UTC),
        actor="user@acme.com",
        action="RAG Evaluate",
        resource="pinecone/query",
        status="blocked",
        risk="high",
        details="movement blocked",
        usage_metadata={"module": "rag_gateway"},
    )
    assert map_audit_source(log) == "rag"


@pytest.mark.asyncio
async def test_evaluate_and_dispatch_creates_ticket() -> None:
    from app.models.governance import AlertWebhook
    from app.services.incident_dispatch_service import evaluate_and_dispatch
    from app.schemas.incident import AdapterResult

    tenant_id = uuid.uuid4()
    webhook = AlertWebhook(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="SNOW",
        webhook_type="servicenow",
        endpoint_url="https://example.service-now.com/api/now/table/incident",
        enabled=True,
        alerts_sent=0,
        tickets_created=0,
        last_error="",
    )
    event = SecurityIncidentEvent(
        event_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        source="gateway",
        action="gateway.policy.block",
        title="Blocked",
        actor="user@acme.com",
        resource="gpt-4",
        status="blocked",
        risk="high",
        details="test",
        occurred_at="2026-08-15T00:00:00Z",
    ).with_fingerprint()

    db = AsyncMock()
    db.commit = AsyncMock()
    db.add = AsyncMock()
    db.flush = AsyncMock()
    db.get = AsyncMock(return_value=None)

    mock_adapter = AsyncMock()
    mock_adapter.create_ticket = AsyncMock(
        return_value=AdapterResult(external_ticket_id="INC001", external_url="https://x/inc/INC001")
    )

    with patch(
        "app.services.incident_dispatch_service.list_webhooks",
        AsyncMock(return_value=[webhook]),
    ), patch(
        "app.services.incident_dispatch_service.get_incident_adapter",
        return_value=mock_adapter,
    ), patch(
        "app.services.incident_dispatch_service._find_outbox_in_window",
        AsyncMock(return_value=None),
    ), patch(
        "app.services.incident_dispatch_service._write_incident_audit",
        AsyncMock(),
    ):
        results = await evaluate_and_dispatch(db, tenant_id, event)

    assert len(results) == 1
    assert results[0]["delivered"]
    assert results[0]["action"] == "created"
    mock_adapter.create_ticket.assert_awaited_once()


@pytest.mark.asyncio
async def test_evaluate_and_dispatch_updates_on_duplicate() -> None:
    from app.models.governance import AlertWebhook, IncidentOutbox
    from app.services.incident_dispatch_service import evaluate_and_dispatch
    from app.schemas.incident import AdapterResult

    tenant_id = uuid.uuid4()
    webhook_id = uuid.uuid4()
    webhook = AlertWebhook(
        id=webhook_id,
        tenant_id=tenant_id,
        name="SNOW",
        webhook_type="servicenow",
        endpoint_url="https://example.service-now.com/api/now/table/incident",
        enabled=True,
        alerts_sent=1,
        tickets_created=1,
        last_error="",
    )
    existing = IncidentOutbox(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        connector_id=webhook_id,
        fingerprint="fp",
        external_ticket_id="sys123",
        event_count=1,
        first_event_at=datetime.now(UTC),
        last_event_at=datetime.now(UTC),
    )
    event = SecurityIncidentEvent(
        event_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        source="gateway",
        action="gateway.policy.block",
        title="Blocked",
        actor="user@acme.com",
        resource="gpt-4",
        status="blocked",
        risk="high",
        details="dup",
        occurred_at="2026-08-15T00:00:00Z",
        fingerprint="fp",
    )

    db = AsyncMock()
    db.commit = AsyncMock()
    db.add = AsyncMock()
    db.flush = AsyncMock()

    mock_adapter = AsyncMock()
    mock_adapter.update_ticket = AsyncMock(return_value=AdapterResult(external_ticket_id="sys123"))

    with patch(
        "app.services.incident_dispatch_service.list_webhooks",
        AsyncMock(return_value=[webhook]),
    ), patch(
        "app.services.incident_dispatch_service.get_incident_adapter",
        return_value=mock_adapter,
    ), patch(
        "app.services.incident_dispatch_service._find_outbox_in_window",
        AsyncMock(return_value=existing),
    ), patch(
        "app.services.incident_dispatch_service._write_incident_audit",
        AsyncMock(),
    ):
        results = await evaluate_and_dispatch(db, tenant_id, event)

    assert results[0]["action"] == "updated"
    mock_adapter.update_ticket.assert_awaited_once()
    assert existing.event_count == 2
