"""Microsoft Copilot governance API — inventory, sync, drift, baselines (Phase 4)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import MANAGE_AGENTS, VIEW_AGENTS, require_any_permission
from app.db.session import get_db
from app.models.copilot import CopilotBaseline, CopilotConnector, CopilotDriftRecord, CopilotInstance
from app.models.tenant import User
from app.schemas.copilot import (
    CopilotBaselineCreateRequest,
    CopilotBaselineResponse,
    CopilotConnectorResponse,
    CopilotDriftResponse,
    CopilotInstanceResponse,
    CopilotSummaryResponse,
    CopilotSyncRequest,
    CopilotSyncResponse,
)
from app.services.copilot_service import (
    acknowledge_drift,
    capture_baseline,
    connector_to_dict,
    copilot_summary,
    detect_drift,
    drift_to_dict,
    instance_to_dict,
    list_drift,
    sync_copilot_payload,
)

router = APIRouter()

_require_copilot_manage = require_any_permission(MANAGE_AGENTS)
_require_copilot_view = require_any_permission(VIEW_AGENTS, MANAGE_AGENTS)


@router.get("/copilot/instances", response_model=list[CopilotInstanceResponse])
async def get_copilot_instances(
    current_user: Annotated[User, Depends(_require_copilot_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    result = await db.execute(
        select(CopilotInstance)
        .where(
            CopilotInstance.tenant_id == current_user.tenant_id,
            CopilotInstance.status != "removed",
        )
        .order_by(CopilotInstance.risk_score.desc())
    )
    return [instance_to_dict(instance) for instance in result.scalars().all()]


@router.get("/copilot/connectors", response_model=list[CopilotConnectorResponse])
async def get_copilot_connectors(
    current_user: Annotated[User, Depends(_require_copilot_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    result = await db.execute(
        select(CopilotConnector)
        .where(
            CopilotConnector.tenant_id == current_user.tenant_id,
            CopilotConnector.status != "removed",
        )
        .order_by(CopilotConnector.risk_score.desc())
    )
    return [connector_to_dict(connector) for connector in result.scalars().all()]


@router.post("/copilot/sync", response_model=CopilotSyncResponse)
async def sync_copilot(
    payload: CopilotSyncRequest,
    current_user: Annotated[User, Depends(_require_copilot_manage)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CopilotSyncResponse:
    sync_result = await sync_copilot_payload(
        db,
        current_user.tenant_id,
        {"instances": payload.instances, "connectors": payload.connectors},
    )
    drift = await detect_drift(db, current_user.tenant_id)
    await db.commit()
    return CopilotSyncResponse(
        instances_upserted=sync_result.instances_upserted,
        instances_removed=sync_result.instances_removed,
        connectors_upserted=sync_result.connectors_upserted,
        connectors_removed=sync_result.connectors_removed,
        drift_found=len(drift),
    )


@router.get("/copilot/drift", response_model=list[CopilotDriftResponse])
async def get_copilot_drift(
    current_user: Annotated[User, Depends(_require_copilot_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
) -> list[dict]:
    records = await list_drift(db, current_user.tenant_id, status=status_filter, severity=severity)
    return [drift_to_dict(record) for record in records]


@router.post("/copilot/drift/{drift_id}/acknowledge", response_model=CopilotDriftResponse)
async def acknowledge_copilot_drift(
    drift_id: uuid.UUID,
    current_user: Annotated[User, Depends(_require_copilot_manage)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    record = await acknowledge_drift(db, current_user.tenant_id, drift_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drift record not found")
    await db.commit()
    return drift_to_dict(record)


@router.post("/copilot/baselines", response_model=CopilotBaselineResponse)
async def create_copilot_baseline(
    payload: CopilotBaselineCreateRequest,
    current_user: Annotated[User, Depends(_require_copilot_manage)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CopilotBaseline:
    baseline = await capture_baseline(
        db,
        current_user.tenant_id,
        name=payload.name,
        created_by=payload.created_by or current_user.email,
    )
    await db.commit()
    return baseline


@router.get("/copilot/baselines", response_model=list[CopilotBaselineResponse])
async def get_copilot_baselines(
    current_user: Annotated[User, Depends(_require_copilot_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CopilotBaseline]:
    result = await db.execute(
        select(CopilotBaseline)
        .where(CopilotBaseline.tenant_id == current_user.tenant_id)
        .order_by(CopilotBaseline.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/copilot/summary", response_model=CopilotSummaryResponse)
async def get_copilot_summary(
    current_user: Annotated[User, Depends(_require_copilot_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await copilot_summary(db, current_user.tenant_id)
