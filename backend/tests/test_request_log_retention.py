"""Tests for full request/response log retention (BL-073)."""

from app.schemas.openai import ChatCompletionRequest, ChatMessage, InspectionResult, PolicyViolation
from app.services.request_log_service import (
    build_guardrail_events,
    serialize_chat_request,
    _truncate_payload,
)


def test_serialize_chat_request_roundtrip() -> None:
    request = ChatCompletionRequest(
        model="gpt-4o",
        messages=[ChatMessage(role="user", content="Hello gateway")],
    )
    payload = serialize_chat_request(request)
    assert payload is not None
    assert payload["model"] == "gpt-4o"
    assert payload["messages"][0]["content"] == "Hello gateway"


def test_build_guardrail_events_includes_violations() -> None:
    ingress = InspectionResult(
        allowed=False,
        action="block",
        violations=[
            PolicyViolation(
                rule_name="block-injection",
                action="block",
                severity="high",
                detail="Prompt injection detected",
            )
        ],
        risk="high",
    )
    events = build_guardrail_events(ingress=ingress)
    assert events is not None
    assert events["ingress"]["allowed"] is False
    assert events["ingress"]["violations"][0]["rule_name"] == "block-injection"


def test_truncate_payload_large_json() -> None:
    huge = {"text": "x" * 70000}
    truncated = _truncate_payload(huge)
    assert truncated["_truncated"] is True
    assert truncated["_original_chars"] > 65536
