import uuid
from datetime import UTC, datetime
from typing import Annotated

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import INGEST_AUDIT_LOGS, VIEW_AUDIT_LOGS, require_permission
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.audit import (
    AuditIngestBatchResponse,
    AuditIngestJobStatusResponse,
    AuditIngestRequest,
    AuditIngestResponse,
    AuditIngestSourceStat,
    SiemConnectorCreateRequest,
    SiemConnectorResponse,
    SiemConnectorUpdateRequest,
    SiemExportResponse,
)
from app.services.audit_ingestion_service import (
    MAX_ASYNC_BATCH,
    audit_ingest_stats,
    ingest_audit_events_sync,
)
from app.services.siem_connector_service import (
    connector_to_dict,
    create_connector,
    delete_connector,
    fetch_logs_for_export,
    get_connector,
    list_connectors,
    run_connector_export,
    update_connector,
)
from app.services.siem_export_service import format_cef_lines, format_json_array, format_ndjson
from app.worker.celery_app import celery_app

router = APIRouter(prefix="/audit", tags=["Audit"])

_require_ingest = require_permission(INGEST_AUDIT_LOGS)
_require_view = require_permission(VIEW_AUDIT_LOGS)


@router.post("/ingest", response_model=AuditIngestResponse)
async def ingest_audit_logs(
    body: AuditIngestRequest,
    current_user: Annotated[User, Depends(_require_ingest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditIngestResponse:
    try:
        result = await ingest_audit_events_sync(
            db,
            current_user.tenant_id,
            [event.model_dump(mode="json") for event in body.events],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AuditIngestResponse(
        accepted=result.accepted,
        skipped=result.skipped,
        duplicates=result.duplicates,
        ids=result.ids,
    )


@router.post("/ingest/batch", response_model=AuditIngestBatchResponse)
async def ingest_audit_logs_batch(
    body: AuditIngestRequest,
    current_user: Annotated[User, Depends(_require_ingest)],
) -> AuditIngestBatchResponse:
    if len(body.events) > MAX_ASYNC_BATCH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch exceeds maximum of {MAX_ASYNC_BATCH} events",
        )

    task = celery_app.send_task(
        "app.worker.tasks.ingest_audit_batch",
        args=[str(current_user.tenant_id), [event.model_dump(mode="json") for event in body.events]],
    )
    return AuditIngestBatchResponse(
        job_id=task.id,
        queued=len(body.events),
        message="Audit batch queued for background ingestion",
    )


@router.get("/ingest/jobs/{job_id}", response_model=AuditIngestJobStatusResponse)
async def get_ingest_job_status(
    job_id: str,
    current_user: Annotated[User, Depends(_require_ingest)],
) -> AuditIngestJobStatusResponse:
    del current_user
    result = AsyncResult(job_id, app=celery_app)
    payload = AuditIngestJobStatusResponse(job_id=job_id, state=result.state)

    if result.failed():
        payload.error = str(result.result) if result.result else "Ingestion job failed"
    elif result.successful() and isinstance(result.result, dict):
        payload.result = AuditIngestResponse(**result.result)

    return payload


@router.get("/ingest/sources", response_model=list[AuditIngestSourceStat])
async def list_ingest_sources(
    current_user: Annotated[User, Depends(_require_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(7, ge=1, le=90),
) -> list[AuditIngestSourceStat]:
    rows = await audit_ingest_stats(db, current_user.tenant_id, days=days)
    return [AuditIngestSourceStat(**row) for row in rows]


@router.get("/export")
async def export_audit_logs(
    current_user: Annotated[User, Depends(_require_view)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("json", pattern="^(?i)(json|ndjson|cef)$"),
    since: str | None = Query(None, description="Return entries after this timestamp (YYYY-MM-DD HH:MM:SS)"),
    limit: int = Query(500, ge=1, le=5000),
) -> Response:
    since_dt: datetime | None = None
    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="since must be formatted as YYYY-MM-DD HH:MM:SS",
            ) from exc

    logs = await fetch_logs_for_export(db, current_user.tenant_id, since=since_dt, limit=limit)
    fmt = format.lower()
    if fmt == "ndjson":
        body = format_ndjson(logs)
        media_type = "application/x-ndjson"
        filename = "audit-export.ndjson"
    elif fmt == "cef":
        body = format_cef_lines(logs)
        media_type = "text/plain"
        filename = "audit-export.cef"
    else:
        body = format_json_array(logs)
        media_type = "application/json"
        filename = "audit-export.json"

    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/siem/connectors", response_model=list[SiemConnectorResponse])
async def list_siem_connectors(
    current_user: Annotated[User, Depends(_require_ingest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SiemConnectorResponse]:
    connectors = await list_connectors(db, current_user.tenant_id)
    return [SiemConnectorResponse(**connector_to_dict(c)) for c in connectors]


@router.post("/siem/connectors", response_model=SiemConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_siem_connector(
    body: SiemConnectorCreateRequest,
    current_user: Annotated[User, Depends(_require_ingest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SiemConnectorResponse:
    try:
        connector = await create_connector(db, current_user.tenant_id, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SiemConnectorResponse(**connector_to_dict(connector))


@router.put("/siem/connectors/{connector_id}", response_model=SiemConnectorResponse)
async def update_siem_connector(
    connector_id: str,
    body: SiemConnectorUpdateRequest,
    current_user: Annotated[User, Depends(_require_ingest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SiemConnectorResponse:
    try:
        connector_uuid = uuid.UUID(connector_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid connector id") from exc

    connector = await get_connector(db, current_user.tenant_id, connector_uuid)
    if connector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")

    try:
        updated = await update_connector(db, connector, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SiemConnectorResponse(**connector_to_dict(updated))


@router.delete("/siem/connectors/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_siem_connector(
    connector_id: str,
    current_user: Annotated[User, Depends(_require_ingest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    try:
        connector_uuid = uuid.UUID(connector_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid connector id") from exc

    connector = await get_connector(db, current_user.tenant_id, connector_uuid)
    if connector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    await delete_connector(db, connector)


@router.post("/siem/connectors/{connector_id}/push", response_model=SiemExportResponse)
async def push_siem_connector(
    connector_id: str,
    current_user: Annotated[User, Depends(_require_ingest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SiemExportResponse:
    try:
        connector_uuid = uuid.UUID(connector_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid connector id") from exc

    connector = await get_connector(db, current_user.tenant_id, connector_uuid)
    if connector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")

    try:
        result = await run_connector_export(db, current_user.tenant_id, connector)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return SiemExportResponse(
        exported=result.exported,
        connector_id=result.connector_id,
        connector_name=result.connector_name,
        message=result.message,
    )


@router.post("/siem/export-all")
async def queue_siem_export_all(
    current_user: Annotated[User, Depends(_require_ingest)],
) -> dict:
    task = celery_app.send_task(
        "app.worker.tasks.export_siem_connectors",
        args=[str(current_user.tenant_id)],
    )
    return {"job_id": task.id, "message": "SIEM export queued for all enabled connectors"}
