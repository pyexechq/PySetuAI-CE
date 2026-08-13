from __future__ import annotations

import asyncio

import httpx

_client: httpx.AsyncClient | None = None
_lock = asyncio.Lock()
_requests = 0
_reused_requests = 0


async def get_http_client() -> httpx.AsyncClient:
    global _client, _requests, _reused_requests
    _requests += 1
    if _client is not None:
        _reused_requests += 1
        return _client
    async with _lock:
        if _client is None:
            _client = httpx.AsyncClient(timeout=180.0)
        else:
            _reused_requests += 1
    return _client


def pool_stats() -> dict[str, float | int | bool]:
    return {
        "pooling_instrumented": True,
        "pool_requests": _requests,
        "pool_reused_requests": _reused_requests,
        "pool_reuse_rate_percent": round(_reused_requests / _requests * 100, 1) if _requests else 0.0,
    }


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None