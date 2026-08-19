"""Datadog Events API adapter.

Datadog events are immutable, so there is no true "update" call. On
duplicate we post a follow-up event carrying the same `aggregation_key`
(the original event id) so Datadog's event correlation groups them
together in the UI, and we keep reporting the original ticket id.
"""

from __future__ import annotations

import httpx

from app.models.governance import AlertWebhook
from app.schemas.incident import AdapterResult, SecurityIncidentEvent

_ALERT_TYPE_BY_RISK = {
    "low": "info",
    "medium": "warning",
    "high": "error",
    "critical": "error",
}


class DatadogAdapter:
    async def create_ticket(self, connector: AlertWebhook, event: SecurityIncidentEvent) -> AdapterResult:
        payload = _build_event_payload(connector, event, aggregation_key=event.fingerprint or event.event_id)
        headers = _auth_headers(connector)
        url = _events_url(connector.endpoint_url)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        event_id = str((body.get("event") or {}).get("id") or "")
        external_url = (body.get("event") or {}).get("url")
        return AdapterResult(
            external_ticket_id=event_id or event.event_id,
            external_url=external_url,
            raw_response=_truncate(body),
        )

    async def update_ticket(
        self, connector: AlertWebhook, ticket_id: str, event: SecurityIncidentEvent
    ) -> AdapterResult:
        payload = _build_event_payload(connector, event, aggregation_key=ticket_id, is_followup=True)
        headers = _auth_headers(connector)
        url = _events_url(connector.endpoint_url)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json() if response.content else {}
        return AdapterResult(external_ticket_id=ticket_id, raw_response=_truncate(body))


def _build_event_payload(
    connector: AlertWebhook,
    event: SecurityIncidentEvent,
    *,
    aggregation_key: str | None,
    is_followup: bool = False,
) -> dict:
    config = connector.config_json or {}
    risk = (event.risk or "medium").lower()
    title = f"PySetu duplicate occurrence: {event.title}" if is_followup else f"PySetu: {event.title}"
    tags = ["pysetu", f"tenant:{event.tenant_slug or event.tenant_id}", f"source:{event.source}", f"risk:{risk}"]
    tags.extend(config.get("tags") or [])
    payload: dict = {
        "title": title[:100],
        "text": (
            f"action={event.action}\nactor={event.actor}\nresource={event.resource}\n"
            f"status={event.status}\ntrace_id={event.trace_id or 'n/a'}\n{event.details}"
        )[:4000],
        "alert_type": _ALERT_TYPE_BY_RISK.get(risk, "warning"),
        "tags": tags,
        "source_type_name": config.get("source_type_name", "pysetu"),
    }
    if config.get("service"):
        payload["service"] = config["service"]
    if aggregation_key:
        payload["aggregation_key"] = aggregation_key
    return payload


def _auth_headers(connector: AlertWebhook) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "User-Agent": "PySetu-Incidents/0.1"}
    api_key = connector.auth_token or ""
    if api_key:
        headers["DD-API-KEY"] = api_key
    config = connector.config_json or {}
    if config.get("application_key"):
        headers["DD-APPLICATION-KEY"] = config["application_key"]
    return headers


def _events_url(endpoint_url: str) -> str:
    base = (endpoint_url or "https://api.datadoghq.com").rstrip("/")
    if base.endswith("/api/v1/events"):
        return base
    return f"{base}/api/v1/events"


def _truncate(body: dict) -> dict:
    if not isinstance(body, dict):
        return {}
    return {k: body[k] for k in list(body.keys())[:8]}
