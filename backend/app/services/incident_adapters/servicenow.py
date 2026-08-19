"""ServiceNow Table API incident adapter."""

from __future__ import annotations

import httpx

from app.models.governance import AlertWebhook
from app.schemas.incident import AdapterResult, SecurityIncidentEvent, incident_event_to_alert_dict
from app.services.alert_webhook_service import build_servicenow_payload


class ServiceNowAdapter:
    async def create_ticket(self, connector: AlertWebhook, event: SecurityIncidentEvent) -> AdapterResult:
        payload = build_servicenow_payload(incident_event_to_alert_dict(event), connector.config_json)
        payload["correlation_id"] = event.fingerprint or event.event_id
        headers = _auth_headers(connector)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(connector.endpoint_url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        result = body.get("result") or {}
        sys_id = str(result.get("sys_id") or result.get("number") or "")
        number = str(result.get("number") or sys_id)
        external_url = None
        if sys_id and connector.endpoint_url:
            base = connector.endpoint_url.rsplit("/api/", 1)[0]
            external_url = f"{base}/nav_to.do?uri=incident.do?sys_id={sys_id}"
        return AdapterResult(
            external_ticket_id=sys_id or number,
            external_url=external_url,
            raw_response=_truncate_body(body),
        )

    async def update_ticket(
        self, connector: AlertWebhook, ticket_id: str, event: SecurityIncidentEvent
    ) -> AdapterResult:
        note = _work_note(event)
        url = _ticket_url(connector.endpoint_url, ticket_id)
        payload = {"work_notes": note}
        headers = _auth_headers(connector)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.patch(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json() if response.content else {}
        return AdapterResult(external_ticket_id=ticket_id, raw_response=_truncate_body(body))


def _auth_headers(connector: AlertWebhook) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "User-Agent": "PySetu-Incidents/0.1"}
    token = connector.auth_token or ""
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _ticket_url(endpoint_url: str, ticket_id: str) -> str:
    base = endpoint_url.rstrip("/")
    if base.endswith("incident"):
        return f"{base}/{ticket_id}"
    return f"{base}/{ticket_id}"


def _work_note(event: SecurityIncidentEvent) -> str:
    return (
        f"PySetu duplicate incident (count update). "
        f"Action={event.action}; actor={event.actor}; resource={event.resource}; "
        f"risk={event.risk}; trace={event.trace_id or 'n/a'}; "
        f"details={event.details[:500]}"
    )


def _truncate_body(body: dict) -> dict:
    if not isinstance(body, dict):
        return {}
    return {k: body[k] for k in list(body.keys())[:8]}
