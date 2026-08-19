import hashlib
import uuid
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_client
from app.db.session import get_db
from app.models.governance import AuditLog, ClientApiKey, PolicyBundle
from app.schemas.extension import (
    ExtensionConfigResponse,
    ExtensionIncidentRequest,
    ExtensionScanRequest,
    ExtensionScanResponse,
)
from app.schemas.incident import SecurityIncidentEvent
from app.services.dlp_service import scan_content as dlp_scan_content
from app.services.incident_dispatch_service import dispatch_security_incident
from app.services.policy_engine import inspect_for_gateway
from app.services.policy_bundle_service import get_tenant_default_bundle
from app.services.request_log_service import store_request_log_body

router = APIRouter()
_BROWSER_BLOCKED_SENSITIVITY = frozenset({"RESTRICTED_PII", "RESTRICTED_PHI", "RESTRICTED_PCI"})


def _safe_resource_url(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return url[:255]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))[:255]


async def _load_bundle(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    bundle_id: uuid.UUID | None,
) -> PolicyBundle | None:
    if not bundle_id:
        return await get_tenant_default_bundle(db, tenant_id)
    result = await db.execute(select(PolicyBundle).where(PolicyBundle.id == bundle_id))
    return result.scalar_one_or_none()


@router.get("/extension/config", response_model=ExtensionConfigResponse)
async def get_extension_config(
    client: Annotated[ClientApiKey, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExtensionConfigResponse:
    bundle = await _load_bundle(db, client.tenant_id, client.bundle_id)
    target_domains = list(bundle.target_domains) if bundle and bundle.target_domains else []
    return ExtensionConfigResponse(bundle_id=str(bundle.id) if bundle else None, target_domains=target_domains)


@router.post("/extension/scan", response_model=ExtensionScanResponse)
async def scan_extension_content(
    payload: ExtensionScanRequest,
    client: Annotated[ClientApiKey, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExtensionScanResponse:
    bundle = await _load_bundle(db, client.tenant_id, client.bundle_id)
    dlp_result = dlp_scan_content(payload.content)
    input_hash = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()
    redacted_content = dlp_result.redacted_content
    inspection = await inspect_for_gateway(
        db,
        client.tenant_id,
        bundle,
        payload.content,
        context={"has_pii": dlp_result.has_pii, "region": dlp_result.region},
    )
    top_violation = inspection.violations[0] if inspection.violations else None
    blocked_label = next(
        (label for label in dlp_result.sensitivity_labels if label in _BROWSER_BLOCKED_SENSITIVITY),
        None,
    )
    if blocked_label:
        if not redacted_content:
            return ExtensionScanResponse(
                allowed=False,
                action="block",
                matched_rule=f"Browser protection: {blocked_label}",
                sensitivity_labels=dlp_result.sensitivity_labels,
                reason=f"{blocked_label} data could not be safely redacted and cannot be sent to external AI websites",
                input_hash=input_hash,
                input_length=len(payload.content),
            )
        return ExtensionScanResponse(
            allowed=True,
            action="redact",
            matched_rule=f"Browser protection: {blocked_label}",
            sensitivity_labels=dlp_result.sensitivity_labels,
            reason=f"{blocked_label} data was redacted before sending to the external AI website",
            redacted_content=redacted_content,
            input_hash=input_hash,
            input_length=len(payload.content),
        )
    return ExtensionScanResponse(
        allowed=inspection.allowed,
        action=inspection.action,
        matched_rule=top_violation.rule_name if top_violation else None,
        sensitivity_labels=dlp_result.sensitivity_labels,
        reason=top_violation.detail if top_violation else "",
        redacted_content=redacted_content,
        input_hash=input_hash,
        input_length=len(payload.content),
    )


@router.post("/extension/incidents", status_code=202)
async def report_extension_incident(
    payload: ExtensionIncidentRequest,
    client: Annotated[ClientApiKey, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    event_id = str(uuid.uuid4())
    risk = "high" if payload.action == "block" else "medium"
    labels = ", ".join(payload.sensitivity_labels)
    resource_url = _safe_resource_url(payload.url)
    audit_log = AuditLog(
        tenant_id=client.tenant_id,
        timestamp=datetime.now(UTC),
        actor=client.name,
        action=f"browser_extension.{payload.action}",
        resource=resource_url,
        status="blocked" if payload.action == "block" else payload.action,
        risk=risk,
        details=(
            f"source=browser_extension; site={payload.site}; "
            f"matched_rule={payload.matched_rule or 'unknown'}; "
            f"sensitivity_labels={labels or 'none'}; event_id={event_id}"
        )[:4000],
        usage_metadata={
            "source": "browser_extension",
            "event_id": event_id,
            "client_key_id": str(client.id),
            "site": payload.site,
            "url": resource_url,
            "matched_rule": payload.matched_rule,
            "sensitivity_labels": payload.sensitivity_labels,
            "snippet_hash": payload.snippet_hash,
            "input_hash": payload.input_hash,
            "input_length": payload.input_length,
        },
        source="browser_extension",
    )
    db.add(audit_log)
    await db.flush()
    await store_request_log_body(
        db,
        tenant_id=client.tenant_id,
        audit_log_id=audit_log.id,
        request_payload={
            "redacted_input": payload.redacted_input or "[INPUT REDACTED]",
            "input_hash": payload.input_hash,
            "input_length": payload.input_length,
        },
    )
    event = SecurityIncidentEvent(
        event_id=event_id,
        tenant_id=str(client.tenant_id),
        source="browser_extension",
        action=f"browser_extension.{payload.action}",
        title=f"Browser extension {payload.action} on {payload.site}",
        actor=client.name,
        resource=resource_url,
        status=payload.action,
        risk=risk,
        matched_rule=payload.matched_rule,
        details=f"Sensitivity labels: {', '.join(payload.sensitivity_labels)}" if payload.sensitivity_labels else "",
        occurred_at=datetime.now(UTC).isoformat(),
    )
    dispatched = await dispatch_security_incident(db, client.tenant_id, event)
    await db.commit()
    return {"dispatched": len(dispatched)}
