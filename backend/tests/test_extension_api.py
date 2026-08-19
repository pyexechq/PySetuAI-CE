import pytest
from pydantic import ValidationError

from app.schemas.extension import (
    ExtensionConfigResponse,
    ExtensionIncidentRequest,
    ExtensionScanRequest,
    ExtensionScanResponse,
)
from app.schemas.incident import DEFAULT_ALLOWED_SOURCES, SecurityIncidentEvent
from app.api.v1.extension import _BROWSER_BLOCKED_SENSITIVITY, _safe_resource_url


def test_extension_config_response_defaults() -> None:
    response = ExtensionConfigResponse()
    assert response.bundle_id is None
    assert response.target_domains == []


def test_extension_scan_request_requires_content() -> None:
    with pytest.raises(ValidationError):
        ExtensionScanRequest()


def test_extension_scan_response_defaults_to_allow() -> None:
    response = ExtensionScanResponse(allowed=True)
    assert response.action == "allow"
    assert response.matched_rule is None
    assert response.sensitivity_labels == []


def test_extension_incident_request_requires_core_fields() -> None:
    payload = ExtensionIncidentRequest(site="chatgpt.com", url="https://chatgpt.com/", action="block")
    assert payload.matched_rule is None
    assert payload.sensitivity_labels == []


def test_browser_extension_is_allowed_incident_source() -> None:
    assert "browser_extension" in DEFAULT_ALLOWED_SOURCES
    event = SecurityIncidentEvent(
        event_id="evt-1",
        tenant_id="tenant-1",
        source="browser_extension",
        action="browser_extension.block",
        title="Blocked",
        actor="ext-key",
        resource="https://chatgpt.com/",
        status="block",
        risk="high",
        occurred_at="2026-08-18T00:00:00+00:00",
    )
    assert event.source == "browser_extension"


def test_restricted_dlp_labels_are_blocked_for_browser_destinations() -> None:
    assert "RESTRICTED_PII" in _BROWSER_BLOCKED_SENSITIVITY
    assert "RESTRICTED_PHI" in _BROWSER_BLOCKED_SENSITIVITY
    assert "RESTRICTED_PCI" in _BROWSER_BLOCKED_SENSITIVITY


def test_extension_audit_url_removes_query_and_fragment() -> None:
    assert _safe_resource_url("https://chatgpt.com/c/abc?token=secret#message") == "https://chatgpt.com/c/abc"


def test_extension_incident_accepts_redacted_input_metadata() -> None:
    payload = ExtensionIncidentRequest(
        site="chatgpt.com",
        url="https://chatgpt.com/",
        action="block",
        redacted_input="My SSN is [REDACTED]",
        input_hash="a" * 64,
        input_length=21,
    )
    assert payload.redacted_input == "My SSN is [REDACTED]"
    assert payload.input_hash == "a" * 64
