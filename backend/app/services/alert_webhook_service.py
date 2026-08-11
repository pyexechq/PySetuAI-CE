"""CRUD and delivery stubs for Slack / ServiceNow alert webhooks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AlertWebhook
from app.services.integration_service import mask_secret

VALID_WEBHOOK_TYPES = frozenset({"slack", "servicenow"})

SAMPLE_EVENT: dict[str, Any] = {
    "title": "HelixGuard test alert",
    "action": "policy.violation",
    "actor": "admin@acme.com",
    "resource": "gpt-4",
    "status": "blocked",
    "risk": "high",
    "details": "Test notification from HelixGuard AI — no action required.",
    "tenant": "acme",
}


@dataclass
class AlertDispatchResult:
    webhook_id: str
    webhook_name: str
    message: str


def webhook_to_dict(webhook: AlertWebhook, *, include_token: bool = False) -> dict:
    return {
        "id": str(webhook.id),
        "name": webhook.name,
        "webhook_type": webhook.webhook_type,
        "endpoint_url": webhook.endpoint_url,
        "channel": webhook.channel,
        "enabled": webhook.enabled,
        "alerts_sent": webhook.alerts_sent,
        "last_alert_at": webhook.last_alert_at.isoformat() if webhook.last_alert_at else None,
        "last_error": webhook.last_error or "",
        "auth_token_set": bool(webhook.auth_token),
        "auth_token_masked": mask_secret(webhook.auth_token) if webhook.auth_token else None,
        **({"auth_token": webhook.auth_token} if include_token else {}),
    }


def build_slack_payload(event: dict[str, Any], *, channel: str | None = None) -> dict[str, Any]:
    risk = str(event.get("risk", "medium")).upper()
    emoji = {"LOW": ":white_check_mark:", "MEDIUM": ":warning:", "HIGH": ":rotating_light:", "CRITICAL": ":fire:"}.get(
        risk, ":bell:"
    )
    text = f"{emoji} *{event.get('title', 'HelixGuard alert')}* — `{event.get('action', 'event')}`"
    blocks: list[dict[str, Any]] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Actor:*\n{event.get('actor', 'unknown')}"},
                {"type": "mrkdwn", "text": f"*Resource:*\n{event.get('resource', 'n/a')}"},
                {"type": "mrkdwn", "text": f"*Status:*\n{event.get('status', 'n/a')}"},
                {"type": "mrkdwn", "text": f"*Risk:*\n{risk}"},
            ],
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": event.get("details", "")[:3000]}},
    ]
    payload: dict[str, Any] = {"text": text, "blocks": blocks}
    if channel:
        payload["channel"] = channel
    return payload


def build_servicenow_payload(event: dict[str, Any]) -> dict[str, Any]:
    risk = str(event.get("risk", "medium")).lower()
    urgency = {"low": "3", "medium": "2", "high": "1", "critical": "1"}.get(risk, "2")
    short = f"HelixGuard: {event.get('action', 'security event')} — {event.get('resource', 'n/a')}"
    description = "\n".join(
        [
            f"Event: {event.get('title', 'HelixGuard alert')}",
            f"Actor: {event.get('actor', 'unknown')}",
            f"Resource: {event.get('resource', 'n/a')}",
            f"Status: {event.get('status', 'n/a')}",
            f"Risk: {risk}",
            "",
            event.get("details", ""),
        ]
    )
    return {
        "short_description": short[:160],
        "description": description[:4000],
        "urgency": urgency,
        "impact": urgency,
        "category": "Security",
        "subcategory": "AI Governance",
        "assignment_group": "Security Operations",
    }


def build_payload(webhook: AlertWebhook, event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    headers = {"Content-Type": "application/json", "User-Agent": "HelixGuard-Alerts/0.1"}
    if webhook.webhook_type == "slack":
        return build_slack_payload(event, channel=webhook.channel), headers
    if webhook.webhook_type == "servicenow":
        token = webhook.auth_token or ""
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return build_servicenow_payload(event), headers
    raise ValueError(f"Unsupported webhook_type: {webhook.webhook_type}")


async def list_webhooks(db: AsyncSession, tenant_id: uuid.UUID) -> list[AlertWebhook]:
    result = await db.execute(
        select(AlertWebhook).where(AlertWebhook.tenant_id == tenant_id).order_by(AlertWebhook.created_at.desc())
    )
    return list(result.scalars().all())


async def get_webhook(db: AsyncSession, tenant_id: uuid.UUID, webhook_id: uuid.UUID) -> AlertWebhook | None:
    result = await db.execute(
        select(AlertWebhook).where(
            AlertWebhook.tenant_id == tenant_id,
            AlertWebhook.id == webhook_id,
        )
    )
    return result.scalar_one_or_none()


async def create_webhook(db: AsyncSession, tenant_id: uuid.UUID, data: dict) -> AlertWebhook:
    webhook_type = str(data.get("webhook_type", "slack")).strip().lower()
    if webhook_type not in VALID_WEBHOOK_TYPES:
        raise ValueError(f"Invalid webhook_type — use one of: {', '.join(sorted(VALID_WEBHOOK_TYPES))}")

    webhook = AlertWebhook(
        tenant_id=tenant_id,
        name=str(data["name"]).strip()[:255],
        webhook_type=webhook_type,
        endpoint_url=str(data["endpoint_url"]).strip()[:1024],
        auth_token=(str(data["auth_token"]).strip() or None) if data.get("auth_token") else None,
        channel=(str(data["channel"]).strip() or None) if data.get("channel") else None,
        enabled=bool(data.get("enabled", True)),
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook


async def update_webhook(db: AsyncSession, webhook: AlertWebhook, data: dict) -> AlertWebhook:
    if "name" in data and data["name"] is not None:
        webhook.name = str(data["name"]).strip()[:255]
    if "webhook_type" in data and data["webhook_type"] is not None:
        webhook_type = str(data["webhook_type"]).strip().lower()
        if webhook_type not in VALID_WEBHOOK_TYPES:
            raise ValueError(f"Invalid webhook_type — use one of: {', '.join(sorted(VALID_WEBHOOK_TYPES))}")
        webhook.webhook_type = webhook_type
    if "endpoint_url" in data and data["endpoint_url"] is not None:
        webhook.endpoint_url = str(data["endpoint_url"]).strip()[:1024]
    if "channel" in data and data["channel"] is not None:
        webhook.channel = str(data["channel"]).strip() or None
    if "enabled" in data and data["enabled"] is not None:
        webhook.enabled = bool(data["enabled"])
    if "auth_token" in data and data["auth_token"] is not None:
        token = str(data["auth_token"]).strip()
        webhook.auth_token = token or None
    await db.commit()
    await db.refresh(webhook)
    return webhook


async def delete_webhook(db: AsyncSession, webhook: AlertWebhook) -> None:
    await db.delete(webhook)
    await db.commit()


async def send_alert(webhook: AlertWebhook, event: dict[str, Any]) -> None:
    payload, headers = build_payload(webhook, event)
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(webhook.endpoint_url, json=payload, headers=headers)
        response.raise_for_status()


async def send_test_alert(
    db: AsyncSession,
    webhook: AlertWebhook,
    *,
    event: dict[str, Any] | None = None,
) -> AlertDispatchResult:
    if not webhook.enabled:
        raise ValueError("Webhook is disabled")

    sample = {**SAMPLE_EVENT, **(event or {})}
    try:
        await send_alert(webhook, sample)
        webhook.alerts_sent += 1
        webhook.last_alert_at = datetime.now(UTC)
        webhook.last_error = ""
        await db.commit()
        return AlertDispatchResult(
            webhook_id=str(webhook.id),
            webhook_name=webhook.name,
            message=f"Test alert sent to {webhook.webhook_type}",
        )
    except httpx.HTTPError as exc:
        webhook.last_error = str(exc)
        await db.commit()
        raise
