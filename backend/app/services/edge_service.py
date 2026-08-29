"""Service layer for Distributed Edge Gateway nodes, bundle sync, and telemetry ingestion."""

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge_gateway import EdgeGatewayNode
from app.models.governance import ClientApiKey, PolicyBundle, RoutingRule
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


def hash_token(raw_token: str) -> str:
    """Hash node enrollment secret."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


CURRENT_GLOBAL_BUNDLE_VERSION = 104


async def list_edge_nodes(db: AsyncSession, tenant_id: Optional[uuid.UUID] = None) -> EdgeNodeListResponse:
    """List all registered edge gateway nodes and aggregated mesh telemetry."""
    query = select(EdgeGatewayNode).order_by(EdgeGatewayNode.created_at.asc())
    if tenant_id:
        query = query.where(EdgeGatewayNode.tenant_id == tenant_id)

    result = await db.execute(query)
    nodes = list(result.scalars().all())

    # If queried globally (no tenant) and completely empty, seed platform default nodes
    if not nodes and tenant_id is None:
        count_res = await db.execute(select(func.count(EdgeGatewayNode.id)))
        total_in_db = count_res.scalar() or 0
        if total_in_db == 0:
            seed_nodes = [
                EdgeGatewayNode(
                    node_id="edge-us-east-01",
                    name="US-East Gateway (N. Virginia)",
                    region="us-east-1",
                    cloud_provider="aws",
                    status="active",
                    ip_address="198.51.100.12",
                    hostname="edge-iad.pysetu.io",
                    enrollment_token_hash=hash_token("edge-secret-us-east"),
                    bundle_version=CURRENT_GLOBAL_BUNDLE_VERSION,
                    last_heartbeat_at=datetime.utcnow(),
                    sync_latency_ms=0.85,
                    requests_routed_24h=142050,
                    cpu_percent=14.2,
                    memory_percent=26.4,
                    is_active=True,
                ),
                EdgeGatewayNode(
                    node_id="edge-eu-central-01",
                    name="EU-Central Gateway (Frankfurt)",
                    region="eu-central-1",
                    cloud_provider="aws",
                    status="active",
                    ip_address="198.51.100.45",
                    hostname="edge-fra.pysetu.io",
                    enrollment_token_hash=hash_token("edge-secret-eu-central"),
                    bundle_version=CURRENT_GLOBAL_BUNDLE_VERSION,
                    last_heartbeat_at=datetime.utcnow(),
                    sync_latency_ms=1.12,
                    requests_routed_24h=98420,
                    cpu_percent=11.8,
                    memory_percent=22.1,
                    is_active=True,
                ),
                EdgeGatewayNode(
                    node_id="edge-ap-northeast-01",
                    name="AP-Northeast Gateway (Tokyo)",
                    region="ap-northeast-1",
                    cloud_provider="aws",
                    status="active",
                    ip_address="198.51.100.88",
                    hostname="edge-nrt.pysetu.io",
                    enrollment_token_hash=hash_token("edge-secret-ap-tokyo"),
                    bundle_version=CURRENT_GLOBAL_BUNDLE_VERSION,
                    last_heartbeat_at=datetime.utcnow(),
                    sync_latency_ms=1.45,
                    requests_routed_24h=64100,
                    cpu_percent=9.5,
                    memory_percent=18.6,
                    is_active=True,
                ),
            ]
            for node in seed_nodes:
                db.add(node)
            await db.commit()
            for node in seed_nodes:
                await db.refresh(node)
            nodes = seed_nodes

    node_responses = [
        EdgeNodeResponse(
            id=str(n.id),
            node_id=n.node_id,
            name=n.name,
            region=n.region,
            cloud_provider=n.cloud_provider,
            status=n.status,
            ip_address=n.ip_address,
            hostname=n.hostname,
            bundle_version=n.bundle_version,
            last_heartbeat_at=n.last_heartbeat_at,
            sync_latency_ms=n.sync_latency_ms,
            requests_routed_24h=n.requests_routed_24h,
            cpu_percent=n.cpu_percent,
            memory_percent=n.memory_percent,
            is_active=n.is_active,
            created_at=n.created_at,
        )
        for n in nodes
    ]

    active_count = sum(1 for n in nodes if n.status == "active" and n.is_active)
    avg_latency = (
        sum(n.sync_latency_ms for n in nodes) / len(nodes) if nodes else 1.0
    )

    return EdgeNodeListResponse(
        nodes=node_responses,
        total_active_nodes=active_count,
        global_sync_healthy=active_count > 0,
        average_edge_latency_ms=round(avg_latency, 2),
    )


async def enroll_edge_node(db: AsyncSession, payload: EdgeNodeCreate) -> EdgeNodeResponse:
    """Enroll a new regional or customer VPC edge gateway node."""
    raw_token = f"pysetu_edge_{secrets.token_urlsafe(32)}"
    token_hash = hash_token(raw_token)
    node_id = f"edge-{payload.region.lower().replace('_', '-')}-{secrets.token_hex(4)}"

    tenant_uuid = uuid.UUID(payload.tenant_id) if payload.tenant_id else None

    node = EdgeGatewayNode(
        tenant_id=tenant_uuid,
        node_id=node_id,
        name=payload.name,
        region=payload.region,
        cloud_provider=payload.cloud_provider,
        status="active",
        ip_address=payload.ip_address,
        hostname=payload.hostname,
        enrollment_token_hash=token_hash,
        bundle_version=CURRENT_GLOBAL_BUNDLE_VERSION,
        last_heartbeat_at=datetime.utcnow(),
        sync_latency_ms=1.0,
        requests_routed_24h=0,
        is_active=True,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)

    return EdgeNodeResponse(
        id=str(node.id),
        node_id=node.node_id,
        name=node.name,
        region=node.region,
        cloud_provider=node.cloud_provider,
        status=node.status,
        ip_address=node.ip_address,
        hostname=node.hostname,
        bundle_version=node.bundle_version,
        last_heartbeat_at=node.last_heartbeat_at,
        sync_latency_ms=node.sync_latency_ms,
        requests_routed_24h=node.requests_routed_24h,
        cpu_percent=node.cpu_percent,
        memory_percent=node.memory_percent,
        is_active=node.is_active,
        created_at=node.created_at,
        enrollment_token=raw_token,
    )


async def process_edge_heartbeat(
    db: AsyncSession, payload: EdgeHeartbeatRequest, raw_token: Optional[str] = None
) -> EdgeHeartbeatResponse:
    """Process heartbeat from an edge gateway node."""
    query = select(EdgeGatewayNode).where(EdgeGatewayNode.node_id == payload.node_id)
    result = await db.execute(query)
    node = result.scalar_one_or_none()

    if node:
        node.last_heartbeat_at = datetime.utcnow()
        if payload.cpu_percent is not None:
            node.cpu_percent = payload.cpu_percent
        if payload.memory_percent is not None:
            node.memory_percent = payload.memory_percent
        if payload.measured_sync_latency_ms is not None:
            node.sync_latency_ms = payload.measured_sync_latency_ms
        if payload.requests_routed_delta > 0:
            node.requests_routed_24h += payload.requests_routed_delta
        node.status = "active"
        await db.commit()

    update_req = (
        payload.bundle_version < CURRENT_GLOBAL_BUNDLE_VERSION
        if node
        else False
    )

    return EdgeHeartbeatResponse(
        status="acknowledged",
        latest_bundle_version=CURRENT_GLOBAL_BUNDLE_VERSION,
        update_required=update_req,
        server_time=datetime.utcnow(),
    )


async def compile_sync_bundle(
    db: AsyncSession, region: str = "us-east-1"
) -> EdgeSyncBundleResponse:
    """Compile policy, client keys, and model aliases into an optimized edge snapshot."""
    # Fetch active client keys
    key_res = await db.execute(
        select(ClientApiKey).where(ClientApiKey.is_active == True)
    )
    keys = key_res.scalars().all()
    key_items = [
        {
            "key_hash": k.key_hash,
            "tenant_id": str(k.tenant_id),
            "name": k.name,
            "rate_limit_rpm": k.ai_rate_limit_rpm or 1000,
            "token_limit_tpm": k.ai_token_limit_tpm or 100000,
        }
        for k in keys
    ]

    # Fetch active routing rules
    rule_res = await db.execute(select(RoutingRule))
    rules = rule_res.scalars().all()
    alias_dict = {r.name: r.target_model for r in rules} if rules else {
        "gpt-4o": "openai/gpt-4o",
        "claude-3-5-sonnet": "anthropic/claude-3-5-sonnet",
        "gemini-1.5-pro": "google/gemini-1.5-pro",
    }

    # Standard DLP rules
    dlp_rules = [
        {"type": "regex", "name": "credit_card", "pattern": r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b", "tag": "[REDACTED_PCI]"},
        {"type": "regex", "name": "ssn", "pattern": r"\b\d{3}-\d{2}-\d{4}\b", "tag": "[REDACTED_SSN]"},
        {"type": "regex", "name": "api_key", "pattern": r"sk-[A-Za-z0-9]{32,}", "tag": "[REDACTED_SECRET]"},
    ]

    # OPA policy rules
    policy_rules = [
        {
            "rule_id": "rule-data-residency-eu",
            "condition": "region == 'eu-central-1' and contains_pii == true",
            "action": "enforce_local_masking",
        },
        {
            "rule_id": "rule-guardian-burst",
            "condition": "burst_rate_3sigma == true",
            "action": "quarantine_429",
        },
    ]

    return EdgeSyncBundleResponse(
        bundle_version=CURRENT_GLOBAL_BUNDLE_VERSION,
        generated_at=datetime.utcnow(),
        region=region,
        client_api_keys=key_items,
        policy_rules=policy_rules,
        model_aliases=alias_dict,
        dlp_patterns=dlp_rules,
    )


async def ingest_edge_telemetry_batch(
    db: AsyncSession, payload: EdgeTelemetryBatchRequest
) -> EdgeTelemetryBatchResponse:
    """Ingest batched telemetry and token statistics asynchronously flushed from edge nodes."""
    count = len(payload.events)
    # Update node requests counter
    query = select(EdgeGatewayNode).where(EdgeGatewayNode.node_id == payload.node_id)
    res = await db.execute(query)
    node = res.scalar_one_or_none()
    if node:
        node.requests_routed_24h += count
        node.last_heartbeat_at = datetime.utcnow()
        await db.commit()

    return EdgeTelemetryBatchResponse(
        status="ingested",
        events_ingested=count,
        acknowledged_at=datetime.utcnow(),
    )


async def delete_edge_node(
    db: AsyncSession, node_id: str, tenant_id: Optional[uuid.UUID] = None
) -> bool:
    """Delete an enrolled edge node."""
    query = select(EdgeGatewayNode).where(EdgeGatewayNode.node_id == node_id)
    if tenant_id:
        query = query.where(EdgeGatewayNode.tenant_id == tenant_id)
    res = await db.execute(query)
    node = res.scalar_one_or_none()
    if not node:
        return False
    await db.delete(node)
    await db.commit()
    return True
