"""Generic JSON webhook incident adapter."""

from __future__ import annotations

import httpx

from app.models.governance import AlertWebhook
from app.schemas.incident import AdapterResult, SecurityIncidentEvent


class GenericWebhookAdapter:
    async def create_ticket(self, connector: AlertWebhook, event: SecurityIncidentEvent) -> AdapterResult:
        envelope = _envelope("create", event, connector.config_json)
        body = await _post(connector, envelope)
        ticket_id = str(
            body.get("ticket_id")
            or body.get("id")
            or body.get("incident_id")
            or event.event_id
        )
        external_url = body.get("url") or body.get("external_url")
        return AdapterResult(
            external_ticket_id=ticket_id,
            external_url=str(external_url) if external_url else None,
            raw_response=_truncate(body),
        )

    async def update_ticket(
        self, connector: AlertWebhook, ticket_id: str, event: SecurityIncidentEvent
    ) -> AdapterResult:
        envelope = _envelope("update", event, connector.config_json, ticket_id=ticket_id)
        body = await _post(connector, envelope)
        return AdapterResult(external_ticket_id=ticket_id, raw_response=_truncate(body))


def _envelope(
    action: str,
    event: SecurityIncidentEvent,
    config: dict | None,
    *,
    ticket_id: str | None = None,
) -> dict:
    data = {
        "action": action,
        "connector": "pysetu_incident",
        "event": event.model_dump(),
    }
    if ticket_id:
        data["ticket_id"] = ticket_id
    if config:
        data["connector_config"] = config
    return data


async def _post(connector: AlertWebhook, payload: dict) -> dict:
    headers = {"Content-Type": "application/json", "User-Agent": "PySetu-Incidents/0.1"}
    token = connector.auth_token or ""
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(connector.endpoint_url, json=payload, headers=headers)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


def _truncate(body: dict) -> dict:
    if not isinstance(body, dict):
        return {}
    return {k: body[k] for k in list(body.keys())[:8]}
