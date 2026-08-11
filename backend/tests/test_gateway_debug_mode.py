"""Gateway debug mode query parameter."""

from app.api.v1.gateway import _is_debug_mode


def test_debug_mode_requires_exact_query_value() -> None:
    assert _is_debug_mode("debug") is True
    assert _is_debug_mode("DEBUG") is True
    assert _is_debug_mode(" production ") is False
    assert _is_debug_mode(None) is False
