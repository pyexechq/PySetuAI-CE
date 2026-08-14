"""Tests for gateway usage metadata hooks."""

from types import SimpleNamespace
from uuid import uuid4

from app.services.gateway_service import _build_usage_metadata


def test_build_usage_metadata_for_client_key() -> None:
    ctx = SimpleNamespace(
        client_api_key_id=uuid4(),
        client_api_key_name="copilot",
        user=None,
    )
    meta = _build_usage_metadata(
        ctx,
        model="gpt-4o",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        latency_ms=420,
    )
    assert meta["auth_type"] == "client_key"
    assert meta["total_tokens"] == 15
    assert meta["client_api_key_name"] == "copilot"


def test_build_usage_metadata_for_jwt_user() -> None:
    ctx = SimpleNamespace(
        client_api_key_id=None,
        client_api_key_name=None,
        user=SimpleNamespace(id=uuid4()),
    )
    meta = _build_usage_metadata(
        ctx,
        model="llama3.2",
        prompt_tokens=3,
        completion_tokens=2,
        total_tokens=5,
        latency_ms=120,
    )
    assert meta["auth_type"] == "jwt"
    assert meta["user_id"] is not None


def test_build_usage_metadata_includes_routing_fields() -> None:
    ctx = SimpleNamespace(
        client_api_key_id=None,
        client_api_key_name=None,
        user=SimpleNamespace(id=uuid4()),
    )
    meta = _build_usage_metadata(
        ctx,
        model="gpt-4o",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        latency_ms=200,
        matched_routing_rule="production-openai",
        routing_strategy="routing_rule",
        upstream="openai",
        requested_model="gpt-4o-mini",
    )
    assert meta["matched_routing_rule"] == "production-openai"
    assert meta["routing_strategy"] == "routing_rule"
    assert meta["upstream"] == "openai"
    assert meta["requested_model"] == "gpt-4o-mini"
