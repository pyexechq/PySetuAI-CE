"""Incident adapter protocol and registry."""

from __future__ import annotations

from typing import Protocol

from app.models.governance import AlertWebhook
from app.schemas.incident import AdapterResult, SecurityIncidentEvent


class IncidentAdapter(Protocol):
    async def create_ticket(self, connector: AlertWebhook, event: SecurityIncidentEvent) -> AdapterResult: ...
    async def update_ticket(
        self, connector: AlertWebhook, ticket_id: str, event: SecurityIncidentEvent
    ) -> AdapterResult: ...


def get_incident_adapter(webhook_type: str) -> IncidentAdapter | None:
    from app.services.incident_adapters.bmc_helix import BmcHelixAdapter
    from app.services.incident_adapters.datadog import DatadogAdapter
    from app.services.incident_adapters.servicenow import ServiceNowAdapter
    from app.services.incident_adapters.webhook import GenericWebhookAdapter

    adapters: dict[str, IncidentAdapter] = {
        "servicenow": ServiceNowAdapter(),
        "bmc_helix": BmcHelixAdapter(),
        "datadog": DatadogAdapter(),
        "webhook": GenericWebhookAdapter(),
    }
    return adapters.get(webhook_type)
