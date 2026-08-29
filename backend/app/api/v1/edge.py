"""FastAPI Router for Distributed AI Gateway Edge Nodes and Control Plane Sync."""

from typing import Annotated, Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_optional_current_user
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.edge import (
    EdgeHeartbeatRequest,
    EdgeHeartbeatResponse,
    EdgeNodeCreate,
    EdgeNodeListResponse,
    EdgeNodeResponse,
    EdgeSyncBundleResponse,
    EdgeTelemetryBatchRequest,
    EdgeTelemetryBatchResponse,
)
from app.services import edge_service

router = APIRouter(prefix="/edge", tags=["Distributed Edge Mesh"])


@router.get("/nodes", response_model=EdgeNodeListResponse)
async def list_nodes(
    current_user: Annotated[Optional[User], Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """List enrolled regional edge gateway nodes (scoped to tenant if authenticated)."""
    tenant_id = (
        current_user.tenant_id
        if current_user and getattr(current_user, "role", "") != "platform_admin"
        else None
    )
    return await edge_service.list_edge_nodes(db, tenant_id=tenant_id)


@router.post("/nodes", response_model=EdgeNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    payload: EdgeNodeCreate,
    current_user: Annotated[Optional[User], Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """Enroll a new regional edge gateway node for the tenant or platform."""
    if current_user and not payload.tenant_id and getattr(current_user, "role", "") != "platform_admin":
        payload.tenant_id = str(current_user.tenant_id)
    return await edge_service.enroll_edge_node(db, payload)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: str,
    current_user: Annotated[Optional[User], Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """Delete an enrolled regional edge gateway node."""
    tenant_id = (
        current_user.tenant_id
        if current_user and getattr(current_user, "role", "") != "platform_admin"
        else None
    )
    deleted = await edge_service.delete_edge_node(db, node_id=node_id, tenant_id=tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Edge node not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/heartbeat", response_model=EdgeHeartbeatResponse)
async def node_heartbeat(
    payload: EdgeHeartbeatRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Heartbeat endpoint invoked by regional edge nodes to report health and latency."""
    return await edge_service.process_edge_heartbeat(db, payload, raw_token=authorization)


@router.get("/bundle", response_model=EdgeSyncBundleResponse)
async def get_sync_bundle(
    region: str = Query(default="us-east-1"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Download compiled OPA Rego policies, client keys, and model aliases for edge node in-memory caching."""
    return await edge_service.compile_sync_bundle(db, region=region)


@router.post("/telemetry/batch", response_model=EdgeTelemetryBatchResponse)
async def ingest_telemetry_batch(
    payload: EdgeTelemetryBatchRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Asynchronously ingest batched token usage, latency metrics, and DLP violation logs from edge gateways."""
    return await edge_service.ingest_edge_telemetry_batch(db, payload)
