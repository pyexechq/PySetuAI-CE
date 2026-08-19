"""Hybrid dedup incident dispatch to ITSM connectors."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog, AlertWebhook, IncidentOutbox
from app.schemas.incident import (
    IncidentDispatchPolicy,
    SecurityIncidentEvent,
    incident_event_to_alert_dict,
    parse_dispatch_policy,
    policy_allows_event,
)
from app.services.incident_adapters.base import get_incident_adapter
from app.services.incident_event_builder import build_security_incident_event_from_audit

logger = logging.getLogger(__name__)

INCIDENT_CONNECTOR_TYPES = frozenset({"servicenow", "bmc_helix", "datadog", "webhook"})
NOTIFY_CONNECTOR_TYPES = frozenset({"slack"})


async def evaluate_and_dispatch(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    event: SecurityIncidentEvent,
) -> list[dict[str, Any]]:
    """Dispatch incident to all matching connectors; never raises."""
    event = event.with_fingerprint()
    from app.services.alert_webhook_service import list_webhooks, send_alert

    webhooks = await list_webhooks(db, tenant_id)
    results: list[dict[str, Any]] = []

    for webhook in webhooks:
        if not webhook.enabled:
            continue

        webhook_type = (webhook.webhook_type or "").lower()
        policy = parse_dispatch_policy(webhook.dispatch_policy_json)

        if webhook_type in NOTIFY_CONNECTOR_TYPES:
            if not policy_allows_event(policy, event):
                continue
            try:
                await send_alert(webhook, incident_event_to_alert_dict(event))
                webhook.alerts_sent += 1
                webhook.last_alert_at = datetime.now(UTC)
                webhook.last_error = ""
                await db.commit()
                results.append(
                    {
                        "webhook_id": str(webhook.id),
                        "webhook_name": webhook.name,
                        "delivered": True,
                        "action": "notify",
                        "message": f"Alert sent to {webhook_type}",
                    }
                )
            except Exception as exc:
                webhook.last_error = str(exc)
                await db.commit()
                logger.warning("Slack notify failed for webhook %s: %s", webhook.id, exc)
                results.append(
                    {
                        "webhook_id": str(webhook.id),
                        "webhook_name": webhook.name,
                        "delivered": False,
                        "action": "notify",
                        "message": str(exc),
                    }
                )
            continue

        if webhook_type not in INCIDENT_CONNECTOR_TYPES:
            continue

        if not policy_allows_event(policy, event):
            continue

        adapter = get_incident_adapter(webhook_type)
        if adapter is None:
            continue

        try:
            result_entry = await _dispatch_to_connector(db, webhook, event, policy, adapter)
            results.append(result_entry)
        except Exception as exc:
            webhook.last_error = str(exc)
            await db.commit()
            logger.warning("Incident dispatch failed for webhook %s: %s", webhook.id, exc)
            results.append(
                {
                    "webhook_id": str(webhook.id),
                    "webhook_name": webhook.name,
                    "delivered": False,
                    "action": "error",
                    "message": str(exc),
                }
            )

    return results


async def _dispatch_to_connector(
    db: AsyncSession,
    webhook: AlertWebhook,
    event: SecurityIncidentEvent,
    policy: IncidentDispatchPolicy,
    adapter: Any,
) -> dict[str, Any]:
    fingerprint = event.fingerprint or ""
    window_start = datetime.now(UTC) - timedelta(minutes=policy.dedup_window_minutes)

    existing = await _find_outbox_in_window(db, webhook, fingerprint, window_start)

    if existing:
        if policy.on_duplicate == "skip":
            return {
                "webhook_id": str(webhook.id),
                "webhook_name": webhook.name,
                "delivered": True,
                "action": "skipped_duplicate",
                "message": "Duplicate within dedup window — skipped",
                "external_ticket_id": existing.external_ticket_id,
            }

        adapter_result = await adapter.update_ticket(webhook, existing.external_ticket_id, event)
        existing.event_count += 1
        existing.last_event_at = datetime.now(UTC)
        if event.event_id:
            try:
                existing.last_event_id = uuid.UUID(event.event_id)
            except ValueError:
                pass
        if adapter_result.external_url:
            existing.external_url = adapter_result.external_url

        webhook.alerts_sent += 1
        webhook.last_alert_at = datetime.now(UTC)
        webhook.last_error = ""
        await db.commit()

        await _write_incident_audit(
            db,
            tenant_id=webhook.tenant_id,
            action="incident.updated",
            webhook=webhook,
            event=event,
            external_ticket_id=existing.external_ticket_id,
        )
        await db.commit()

        return {
            "webhook_id": str(webhook.id),
            "webhook_name": webhook.name,
            "delivered": True,
            "action": "updated",
            "message": f"Updated ticket {existing.external_ticket_id}",
            "external_ticket_id": existing.external_ticket_id,
        }

    adapter_result = await adapter.create_ticket(webhook, event)
    now = datetime.now(UTC)
    outbox = IncidentOutbox(
        tenant_id=webhook.tenant_id,
        connector_id=webhook.id,
        fingerprint=fingerprint,
        external_ticket_id=adapter_result.external_ticket_id,
        external_url=adapter_result.external_url,
        event_count=1,
        first_event_at=now,
        last_event_at=now,
        last_event_id=_parse_uuid(event.event_id),
    )
    db.add(outbox)

    webhook.tickets_created += 1
    webhook.alerts_sent += 1
    webhook.last_alert_at = now
    webhook.last_error = ""
    await db.commit()

    await _write_incident_audit(
        db,
        tenant_id=webhook.tenant_id,
        action="incident.created",
        webhook=webhook,
        event=event,
        external_ticket_id=adapter_result.external_ticket_id,
    )
    await db.commit()

    return {
        "webhook_id": str(webhook.id),
        "webhook_name": webhook.name,
        "delivered": True,
        "action": "created",
        "message": f"Created ticket {adapter_result.external_ticket_id}",
        "external_ticket_id": adapter_result.external_ticket_id,
    }


async def _find_outbox_in_window(
    db: AsyncSession,
    webhook: AlertWebhook,
    fingerprint: str,
    window_start: datetime,
) -> IncidentOutbox | None:
    result = await db.execute(
        select(IncidentOutbox)
        .where(
            IncidentOutbox.tenant_id == webhook.tenant_id,
            IncidentOutbox.connector_id == webhook.id,
            IncidentOutbox.fingerprint == fingerprint,
            IncidentOutbox.last_event_at >= window_start,
        )
        .order_by(IncidentOutbox.last_event_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _write_incident_audit(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    action: str,
    webhook: AlertWebhook,
    event: SecurityIncidentEvent,
    external_ticket_id: str,
) -> None:
    log = AuditLog(
        tenant_id=tenant_id,
        timestamp=datetime.now(UTC),
        actor="system",
        action=action,
        resource=f"connector/{webhook.name}",
        status="allowed",
        risk=event.risk,
        details=(
            f"connector={webhook.webhook_type}; ticket={external_ticket_id}; "
            f"fingerprint={event.fingerprint}; source={event.source}; action={event.action}"
        )[:4000],
        usage_metadata={
            "incident_event": event.model_dump(),
            "external_ticket_id": external_ticket_id,
            "connector_id": str(webhook.id),
        },
        source="internal",
    )
    db.add(log)
    await db.flush()


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def dispatch_security_incident_from_audit(
    db: AsyncSession,
    audit_log: AuditLog,
    *,
    tenant_slug: str | None = None,
) -> list[dict[str, Any]]:
    from app.schemas.incident import risk_meets_minimum

    if not risk_meets_minimum(audit_log.risk or "low", "high"):
        return []
    event = build_security_incident_event_from_audit(audit_log, tenant_slug=tenant_slug)
    return await evaluate_and_dispatch(db, audit_log.tenant_id, event)


async def dispatch_security_incident(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    event: SecurityIncidentEvent,
) -> list[dict[str, Any]]:
    return await evaluate_and_dispatch(db, tenant_id, event)
