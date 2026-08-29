"""Unit tests for Distributed Edge Gateway Mesh, Bundle Sync, and Telemetry Ingestion."""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.models.edge_gateway import EdgeGatewayNode
from app.schemas.edge import (
    EdgeHeartbeatRequest,
    EdgeNodeCreate,
    EdgeSyncBundleResponse,
    EdgeTelemetryBatchRequest,
    EdgeTelemetryEvent,
)
from app.services import edge_service


def test_edge_gateway_node_model():
    """Test EdgeGatewayNode model fields and defaults."""
    node_id = "edge-us-east-01"
    node = EdgeGatewayNode(
        node_id=node_id,
        name="US East Gateway",
        region="us-east-1",
        cloud_provider="aws",
        status="active",
        sync_latency_ms=0.85,
        requests_routed_24h=5000,
        bundle_version=104,
        is_active=True,
    )
    assert node.node_id == "edge-us-east-01"
    assert node.region == "us-east-1"
    assert node.bundle_version == 104
    assert node.sync_latency_ms == 0.85


def test_edge_node_enrollment_service():
    """Test enrolling a new regional edge gateway node via service."""
    async def _run():
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        
        async def _mock_refresh(instance):
            if not instance.id:
                instance.id = uuid.uuid4()
            if not instance.created_at:
                instance.created_at = datetime.now(timezone.utc)
        
        mock_db.refresh = _mock_refresh

        payload = EdgeNodeCreate(
            name="APAC Sydney Gateway",
            region="ap-southeast-2",
            cloud_provider="aws",
            hostname="edge-syd.pysetu.io",
            ip_address="198.51.100.99",
        )
        res = await edge_service.enroll_edge_node(mock_db, payload)
        assert res.name == "APAC Sydney Gateway"
        assert res.region == "ap-southeast-2"
        assert res.status == "active"
        assert res.enrollment_token is not None
        assert res.enrollment_token.startswith("pysetu_edge_")

    asyncio.run(_run())


def test_edge_heartbeat_service():
    """Test edge node heartbeat report via service."""
    async def _run():
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        payload = EdgeHeartbeatRequest(
            node_id="edge-us-east-01",
            bundle_version=104,
            cpu_percent=18.5,
            memory_percent=32.1,
            requests_routed_delta=150,
            measured_sync_latency_ms=0.92,
        )
        res = await edge_service.process_edge_heartbeat(mock_db, payload)
        assert res.status == "acknowledged"
        assert res.latest_bundle_version >= 104
        assert res.update_required is False

    asyncio.run(_run())


def test_edge_sync_bundle_compilation():
    """Test compiling OPA/key sync bundle for edge caching."""
    async def _run():
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        res = await edge_service.compile_sync_bundle(mock_db, region="eu-central-1")
        assert res.region == "eu-central-1"
        assert res.bundle_version >= 100
        assert len(res.policy_rules) >= 2
        assert "gpt-4o" in res.model_aliases
        assert len(res.dlp_patterns) >= 3

    asyncio.run(_run())


def test_edge_telemetry_batch_service():
    """Test asynchronous batched telemetry ingestion from edge nodes."""
    async def _run():
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        payload = EdgeTelemetryBatchRequest(
            node_id="edge-eu-central-01",
            batch_id="batch-eu-9921",
            events=[
                EdgeTelemetryEvent(
                    client_key_hash="keyhash123",
                    model="gpt-4o",
                    provider="openai",
                    prompt_tokens=120,
                    completion_tokens=45,
                    total_tokens=165,
                    latency_ms=280.5,
                    status_code=200,
                    dlp_violations=[],
                    anomaly_flagged=False,
                ),
                EdgeTelemetryEvent(
                    client_key_hash="keyhash456",
                    model="claude-3-5-sonnet",
                    provider="anthropic",
                    prompt_tokens=300,
                    completion_tokens=110,
                    total_tokens=410,
                    latency_ms=420.0,
                    status_code=200,
                    dlp_violations=["CREDIT_CARD"],
                    anomaly_flagged=False,
                ),
            ],
        )
        res = await edge_service.ingest_edge_telemetry_batch(mock_db, payload)
        assert res.status == "ingested"
        assert res.events_ingested == 2

    asyncio.run(_run())
