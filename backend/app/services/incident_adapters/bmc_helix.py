"""BMC Helix ITSM incident adapter."""

from __future__ import annotations

import httpx

from app.models.governance import AlertWebhook
from app.schemas.incident import AdapterResult, SecurityIncidentEvent


class BmcHelixAdapter:
    async def create_ticket(self, connector: AlertWebhook, event: SecurityIncidentEvent) -> AdapterResult:
        config = connector.config_json or {}
        risk = (event.risk or "medium").lower()
        urgency = {"low": "4", "medium": "3", "high": "2", "critical": "1"}.get(risk, "3")
        payload = {
            "values": {
                "Description": event.details[:4000],
                "Detailed_Decription": event.details[:4000],
                "Short Description": f"PySetu: {event.action} — {event.resource}"[:100],
                "Impact": urgency,
                "Urgency": urgency,
                "Status": "New",
                "Reported Source": "Direct Input",
                "Service_Type": "User Service Restoration",
                "Company": config.get("company", ""),
                "Assigned Group": config.get("assigned_group", "Security"),
                "Login_ID": config.get("login_id", event.actor),
            }
        }
        headers = _auth_headers(connector)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(connector.endpoint_url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        values = body.get("values") or body.get("result") or body
        ticket_id = str(
            values.get("Incident Number")
            or values.get("Request ID")
            or values.get("Entry ID")
            or body.get("Entry ID")
            or ""
        )
        return AdapterResult(external_ticket_id=ticket_id or event.event_id, raw_response=_truncate(body))


    async def update_ticket(
        self, connector: AlertWebhook, ticket_id: str, event: SecurityIncidentEvent
    ) -> AdapterResult:
        config = connector.config_json or {}
        note = (
            f"PySetu duplicate: {event.action}; actor={event.actor}; "
            f"resource={event.resource}; {event.details[:500]}"
        )
        payload = {
            "values": {
                "Incident Number": ticket_id,
                "Work Info": note,
                "Login_ID": config.get("login_id", event.actor),
            }
        }
        headers = _auth_headers(connector)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.put(connector.endpoint_url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json() if response.content else {}
        return AdapterResult(external_ticket_id=ticket_id, raw_response=_truncate(body))


def _auth_headers(connector: AlertWebhook) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "User-Agent": "PySetu-Incidents/0.1"}
    token = connector.auth_token or ""
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _truncate(body: dict) -> dict:
    if not isinstance(body, dict):
        return {}
    return {k: body[k] for k in list(body.keys())[:8]}
