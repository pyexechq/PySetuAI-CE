"""Shared MCP transport helpers for health checks and JSON-RPC clients."""

from __future__ import annotations


def resolve_timeout_sec(connection_config: dict | None) -> float:
    config = connection_config or {}
    try:
        timeout_sec = int(config.get("timeout_sec", 30))
    except (TypeError, ValueError):
        timeout_sec = 30
    return float(max(5, min(timeout_sec, 120)))


def build_mcp_headers(connection_config: dict | None, *, json_rpc: bool = False) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "User-Agent": "HelixGuard-MCP/1.0",
    }
    if json_rpc:
        headers["Content-Type"] = "application/json"
    config = connection_config or {}
    auth_header = config.get("auth_header")
    if isinstance(auth_header, str) and auth_header.strip():
        headers["Authorization"] = auth_header.strip()
    return headers
