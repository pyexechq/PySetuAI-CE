"""Tests for observability trace helpers."""

import uuid

from app.api.v1.observability import extract_trace_id


def test_extract_trace_id_from_prefixed_details() -> None:
    log_id = uuid.uuid4()
    details = "trace_id=abc123def456; Routed to llama3.2 via ollama"
    assert extract_trace_id(details, log_id) == "abc123def456"


def test_extract_trace_id_from_gateway_audit_details() -> None:
    log_id = uuid.uuid4()
    details = (
        "client_key=Test; bundle=Strict Security; "
        "trace_id=472fe65748a6f412e1196802c9adf564; Routed to llama3.2 via ollama"
    )
    assert extract_trace_id(details, log_id) == "472fe65748a6f412e1196802c9adf564"


def test_extract_trace_id_falls_back_to_log_prefix() -> None:
    log_id = uuid.UUID("686e60a4-0c90-48b4-9033-648296b57275")
    assert extract_trace_id("Customer query processed", log_id) == "trace-686e60a4"
