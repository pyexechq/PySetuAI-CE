"""Tests for live MCP trust/risk scoring (BL-051)."""

import uuid

from app.models.governance import MCPServer
from app.services.mcp_trust_scoring_service import (
    compute_mcp_trust_risk_scores,
    record_mcp_invoke_outcome,
    refresh_mcp_trust_scores,
)


def _server(**overrides) -> MCPServer:
    server = MCPServer(
        tenant_id=overrides.pop("tenant_id", uuid.uuid4()),
        name="Test MCP",
        category="productivity",
    )
    server.status = overrides.get("status", "healthy")
    server.success_rate = overrides.get("success_rate", 98.0)
    server.avg_latency_ms = overrides.get("avg_latency_ms", 120)
    server.total_calls = overrides.get("total_calls", 10)
    server.trust_score = overrides.get("trust_score", 0.0)
    server.risk_score = overrides.get("risk_score", 0.0)
    return server


def test_offline_server_has_low_trust_and_high_risk() -> None:
    server = _server(status="offline", success_rate=40.0)
    trust, risk = compute_mcp_trust_risk_scores(server)
    assert trust < 40.0
    assert risk > 60.0


def test_refresh_mcp_trust_scores_updates_server_fields() -> None:
    server = _server(status="healthy", success_rate=99.0, avg_latency_ms=80)
    refresh_mcp_trust_scores(server)
    assert server.trust_score > 80.0
    assert server.risk_score < 20.0


def test_record_mcp_invoke_outcome_tracks_failures() -> None:
    server = _server(status="healthy", success_rate=100.0, total_calls=4)
    record_mcp_invoke_outcome(server, ok=False)
    assert server.total_calls == 5
    assert server.success_rate == 80.0
    assert server.status == "degraded"
    assert server.risk_score >= 30.0
