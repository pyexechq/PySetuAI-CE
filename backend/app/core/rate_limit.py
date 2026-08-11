"""Redis-backed fixed-window rate limiting for auth endpoints."""

from __future__ import annotations

import logging
from typing import Final

import redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

logger = logging.getLogger(__name__)

AUTH_RATE_LIMIT_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/oidc/callback",
        "/api/v1/auth/oidc/authorize",
    }
)

_redis_client: redis.Redis | None = None
_redis_unavailable = False


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _get_redis() -> redis.Redis | None:
    global _redis_client, _redis_unavailable

    if not settings.rate_limit_enabled:
        return None
    if _redis_unavailable:
        return None
    if _redis_client is not None:
        return _redis_client

    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except redis.RedisError as exc:
        _redis_unavailable = True
        logger.warning("Rate limiting disabled: Redis unavailable (%s)", exc)
        return None


def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds). Fail open when Redis is unavailable."""
    client = _get_redis()
    if client is None:
        return True, 0

    try:
        count = client.incr(key)
        if count == 1:
            client.expire(key, window_seconds)
        if count > limit:
            ttl = client.ttl(key)
            return False, max(int(ttl), 1)
        return True, 0
    except redis.RedisError as exc:
        logger.warning("Rate limit check failed, allowing request (%s)", exc)
        return True, 0


def reset_rate_limit_state_for_tests() -> None:
    global _redis_client, _redis_unavailable
    _redis_client = None
    _redis_unavailable = False


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        if path not in AUTH_RATE_LIMIT_PATHS:
            return await call_next(request)

        limit = (
            settings.rate_limit_login_requests
            if path.endswith("/auth/login")
            else settings.rate_limit_auth_requests
        )
        window = settings.rate_limit_window_seconds
        key = f"helixguard:ratelimit:{path}:{client_ip(request)}"
        allowed, retry_after = check_rate_limit(key, limit=limit, window_seconds=window)

        if allowed:
            return await call_next(request)

        return JSONResponse(
            status_code=429,
            content={"detail": "Too many authentication attempts. Please try again later."},
            headers={"Retry-After": str(retry_after)},
        )
