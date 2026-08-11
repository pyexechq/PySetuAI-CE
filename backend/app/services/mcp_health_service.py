"""Probe registered MCP server endpoints for reachability."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.models.governance import MCPServer
from app.services.mcp_transport import build_mcp_headers, resolve_timeout_sec
from app.services.mcp_trust_scoring_service import refresh_mcp_trust_scores


@dataclass
class McpHealthResult:
    ok: bool
    status: str
    latency_ms: int
    message: str
    http_status: int | None = None
    skipped: bool = False


async def probe_mcp_server(server: MCPServer) -> McpHealthResult:
    transport = (server.transport or "sse").strip().lower()

    if transport == "stdio":
        return McpHealthResult(
            ok=True,
            status=server.status,
            latency_ms=0,
            message="Stdio transport uses a local MCP agent; remote endpoint probe skipped.",
            skipped=True,
        )

    endpoint = (server.endpoint_url or "").strip()
    if not endpoint:
        return McpHealthResult(
            ok=False,
            status="offline",
            latency_ms=0,
            message="No endpoint URL configured for this server.",
        )

    timeout_sec = resolve_timeout_sec(server.connection_config)
    headers = build_mcp_headers(server.connection_config)
    started = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            response = await client.get(endpoint, headers=headers)
            latency_ms = max(1, int((time.perf_counter() - started) * 1000))

            if response.status_code < 400:
                return McpHealthResult(
                    ok=True,
                    status="healthy",
                    latency_ms=latency_ms,
                    message=f"Endpoint reachable (HTTP {response.status_code}).",
                    http_status=response.status_code,
                )
            if response.status_code in {401, 403}:
                return McpHealthResult(
                    ok=False,
                    status="degraded",
                    latency_ms=latency_ms,
                    message=f"Endpoint reachable but authorization failed (HTTP {response.status_code}).",
                    http_status=response.status_code,
                )
            return McpHealthResult(
                ok=False,
                status="degraded",
                latency_ms=latency_ms,
                message=f"Endpoint returned HTTP {response.status_code}.",
                http_status=response.status_code,
            )
    except httpx.TimeoutException:
        return McpHealthResult(
            ok=False,
            status="offline",
            latency_ms=int(timeout_sec * 1000),
            message=f"Connection timed out after {int(timeout_sec)}s.",
        )
    except httpx.ConnectError as exc:
        return McpHealthResult(
            ok=False,
            status="offline",
            latency_ms=0,
            message=f"Connection failed: {exc}",
        )
    except httpx.HTTPError as exc:
        return McpHealthResult(
            ok=False,
            status="offline",
            latency_ms=0,
            message=f"HTTP error: {exc}",
        )


def apply_health_result(server: MCPServer, result: McpHealthResult) -> None:
    if result.skipped:
        return
    server.status = result.status
    if result.latency_ms > 0:
        server.avg_latency_ms = result.latency_ms
    refresh_mcp_trust_scores(server)
