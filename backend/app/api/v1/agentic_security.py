"""Advanced agentic security API — anomalies, prompt-injection, exfiltration, guardian (Phase 5)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import MANAGE_AGENTS, VIEW_AGENTS, VIEW_AUDIT_LOGS, require_any_permission
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.agentic_security import (
    AgentAnomalyResponse,
    AgentAnomalySummary,
    ExfiltrationEventResponse,
    ExfiltrationEventSummary,
    GuardianActionResponse,
    GuardianRunResponse,
    GuardianSummary,
    PromptInjectionFindingResponse,
    PromptInjectionFindingSummary,
    PromptInjectionScanRequest,
    PromptInjectionScanResponse,
)
from app.services.anomaly_detection_service import (
    acknowledge_anomaly,
    anomaly_summary,
    anomaly_to_dict,
    list_anomalies,
)
from app.services.exfiltration_detection_service import (
    acknowledge_exfil,
    exfil_summary,
    exfil_to_dict,
    list_exfil_events,
)
from app.services.guardian_service import (
    execute_remediation,
    guardian_action_to_dict,
    guardian_summary,
    list_guardian_actions,
    run_guardian_loop,
)
from app.services.prompt_injection_scan_service import (
    acknowledge_finding,
    finding_summary,
    finding_to_dict,
    list_findings,
    scan_text,
)

router = APIRouter()

_require_security_manage = require_any_permission(MANAGE_AGENTS)
_require_security_view = require_any_permission(VIEW_AGENTS, VIEW_AUDIT_LOGS, MANAGE_AGENTS)


@router.get("/agentic-security/anomalies", response_model=list[AgentAnomalyResponse])
async def get_anomalies(
    current_user: Annotated[User, Depends(_require_security_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    anomaly_type: str | None = Query(default=None),
) -> list[dict]:
    records = await list_anomalies(
        db, current_user.tenant_id, status=status_filter, severity=severity, anomaly_type=anomaly_type
    )
    return [anomaly_to_dict(record) for record in records]


@router.get("/agentic-security/anomalies/summary", response_model=AgentAnomalySummary)
async def get_anomaly_summary(
    current_user: Annotated[User, Depends(_require_security_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await anomaly_summary(db, current_user.tenant_id)


@router.post("/agentic-security/anomalies/{anomaly_id}/acknowledge", response_model=AgentAnomalyResponse)
async def acknowledge_anomaly_route(
    anomaly_id: uuid.UUID,
    current_user: Annotated[User, Depends(_require_security_manage)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    record = await acknowledge_anomaly(db, current_user.tenant_id, anomaly_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomaly not found")
    await db.commit()
    return anomaly_to_dict(record)


@router.get("/agentic-security/prompt-injection", response_model=list[PromptInjectionFindingResponse])
async def get_prompt_injection_findings(
    current_user: Annotated[User, Depends(_require_security_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
) -> list[dict]:
    findings = await list_findings(
        db, current_user.tenant_id, status=status_filter, severity=severity, target_type=target_type
    )
    return [finding_to_dict(finding) for finding in findings]


@router.get("/agentic-security/prompt-injection/summary", response_model=PromptInjectionFindingSummary)
async def get_prompt_injection_summary(
    current_user: Annotated[User, Depends(_require_security_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await finding_summary(db, current_user.tenant_id)


@router.post("/agentic-security/prompt-injection/scan", response_model=PromptInjectionScanResponse)
async def scan_prompt_injection(
    payload: PromptInjectionScanRequest,
    current_user: Annotated[User, Depends(_require_security_manage)],
) -> PromptInjectionScanResponse:
    finding = scan_text(payload.content, target_type=payload.target_type, target=payload.target)
    return PromptInjectionScanResponse(
        detected=finding["detected"],
        highest_severity=finding["highest_severity"],
        recommended_action=finding["recommended_action"],
        matches=finding["matches"],
    )


@router.post("/agentic-security/prompt-injection/{finding_id}/acknowledge", response_model=PromptInjectionFindingResponse)
async def acknowledge_prompt_injection_route(
    finding_id: uuid.UUID,
    current_user: Annotated[User, Depends(_require_security_manage)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    finding = await acknowledge_finding(db, current_user.tenant_id, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    await db.commit()
    return finding_to_dict(finding)


@router.get("/agentic-security/exfiltration", response_model=list[ExfiltrationEventResponse])
async def get_exfiltration_events(
    current_user: Annotated[User, Depends(_require_security_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    exfil_type: str | None = Query(default=None),
) -> list[dict]:
    events = await list_exfil_events(db, current_user.tenant_id, status=status_filter, exfil_type=exfil_type)
    return [exfil_to_dict(event) for event in events]


@router.get("/agentic-security/exfiltration/summary", response_model=ExfiltrationEventSummary)
async def get_exfiltration_summary(
    current_user: Annotated[User, Depends(_require_security_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await exfil_summary(db, current_user.tenant_id)


@router.post("/agentic-security/exfiltration/{exfil_id}/acknowledge", response_model=ExfiltrationEventResponse)
async def acknowledge_exfiltration_route(
    exfil_id: uuid.UUID,
    current_user: Annotated[User, Depends(_require_security_manage)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    event = await acknowledge_exfil(db, current_user.tenant_id, exfil_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exfiltration event not found")
    await db.commit()
    return exfil_to_dict(event)


@router.get("/agentic-security/guardian/actions", response_model=list[GuardianActionResponse])
async def get_guardian_actions(
    current_user: Annotated[User, Depends(_require_security_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    action_type: str | None = Query(default=None),
) -> list[dict]:
    actions = await list_guardian_actions(
        db, current_user.tenant_id, status=status_filter, action_type=action_type
    )
    return [guardian_action_to_dict(action) for action in actions]


@router.get("/agentic-security/guardian/summary", response_model=GuardianSummary)
async def get_guardian_summary(
    current_user: Annotated[User, Depends(_require_security_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await guardian_summary(db, current_user.tenant_id)


@router.post("/agentic-security/guardian/run", response_model=GuardianRunResponse)
async def run_guardian_loop_route(
    current_user: Annotated[User, Depends(_require_security_manage)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await run_guardian_loop(db, current_user.tenant_id)
    await db.commit()
    return result


@router.post("/agentic-security/guardian/actions/{action_id}/execute", response_model=GuardianActionResponse)
async def execute_guardian_action_route(
    action_id: uuid.UUID,
    current_user: Annotated[User, Depends(_require_security_manage)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from app.models.agentic import GuardianAction
    from sqlalchemy import select

    result = await db.execute(
        select(GuardianAction).where(
            GuardianAction.tenant_id == current_user.tenant_id,
            GuardianAction.id == action_id,
        )
    )
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardian action not found")
    await execute_remediation(db, current_user.tenant_id, action)
    await db.commit()
    return guardian_action_to_dict(action)
