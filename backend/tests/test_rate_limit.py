from unittest.mock import MagicMock, patch

from app.core.rate_limit import AUTH_RATE_LIMIT_PATHS, check_rate_limit, client_ip, reset_rate_limit_state_for_tests


def test_auth_rate_limit_paths_include_login() -> None:
    assert "/api/v1/auth/login" in AUTH_RATE_LIMIT_PATHS


def test_client_ip_uses_forwarded_header() -> None:
    request = MagicMock()
    request.headers = {"x-forwarded-for": "203.0.113.10, 10.0.0.1"}
    request.client = MagicMock(host="127.0.0.1")
    assert client_ip(request) == "203.0.113.10"


@patch("app.core.rate_limit._get_redis")
def test_check_rate_limit_allows_under_limit(mock_get_redis: MagicMock) -> None:
    reset_rate_limit_state_for_tests()
    redis_client = MagicMock()
    redis_client.incr.return_value = 1
    redis_client.expire.return_value = True
    mock_get_redis.return_value = redis_client

    allowed, retry_after = check_rate_limit("test-key", limit=10, window_seconds=60)

    assert allowed is True
    assert retry_after == 0
    redis_client.incr.assert_called_once_with("test-key")
    redis_client.expire.assert_called_once_with("test-key", 60)


@patch("app.core.rate_limit._get_redis")
def test_check_rate_limit_blocks_over_limit(mock_get_redis: MagicMock) -> None:
    reset_rate_limit_state_for_tests()
    redis_client = MagicMock()
    redis_client.incr.return_value = 11
    redis_client.ttl.return_value = 42
    mock_get_redis.return_value = redis_client

    allowed, retry_after = check_rate_limit("test-key", limit=10, window_seconds=60)

    assert allowed is False
    assert retry_after == 42
