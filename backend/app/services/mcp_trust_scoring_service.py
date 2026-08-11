"""Live MCP trust and risk scoring from health probes and invocation metrics."""

from __future__ import annotations

from app.models.governance import MCPServer

_STATUS_TRUST = {
    "healthy": 92.0,
    "degraded": 58.0,
    "offline": 18.0,
}


def compute_mcp_trust_risk_scores(server: MCPServer) -> tuple[float, float]:
    """Derive trust (higher is better) and risk (higher is worse) scores from live signals."""
    status = (server.status or "healthy").strip().lower()
    success_rate = max(0.0, min(100.0, float(server.success_rate or 0.0)))
    status_trust = _STATUS_TRUST.get(status, 50.0)

    latency_ms = max(0, int(server.avg_latency_ms or 0))
    latency_penalty = min(20.0, latency_ms / 150.0)

    trust = (success_rate * 0.55) + (status_trust * 0.45) - (latency_penalty * 0.35)
    trust = max(0.0, min(100.0, trust))

    risk = 100.0 - trust
    if status == "offline":
        risk += 12.0
    elif status == "degraded":
        risk += 6.0
    if success_rate < 95.0:
        risk += (95.0 - success_rate) * 0.25

    return round(trust, 1), round(max(0.0, min(100.0, risk)), 1)


def refresh_mcp_trust_scores(server: MCPServer) -> None:
    trust, risk = compute_mcp_trust_risk_scores(server)
    server.trust_score = trust
    server.risk_score = risk


def record_mcp_invoke_outcome(server: MCPServer, *, ok: bool, latency_ms: int = 0) -> None:
    """Update call counters, success rate, status, and derived trust/risk scores."""
    previous_calls = int(server.total_calls or 0)
    server.total_calls = previous_calls + 1

    previous_successes = (float(server.success_rate or 0.0) / 100.0) * previous_calls
    if ok:
        previous_successes += 1.0
        if latency_ms > 0:
            if server.avg_latency_ms:
                server.avg_latency_ms = int((server.avg_latency_ms + latency_ms) / 2)
            else:
                server.avg_latency_ms = latency_ms
        current_status = (server.status or "healthy").lower()
        if current_status == "offline":
            server.status = "degraded"
        elif current_status == "degraded":
            server.status = "healthy"
    elif (server.status or "healthy").lower() == "healthy":
        server.status = "degraded"

    server.success_rate = round(previous_successes / server.total_calls * 100, 1)
    refresh_mcp_trust_scores(server)
