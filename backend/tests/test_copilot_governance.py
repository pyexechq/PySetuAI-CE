"""Unit tests for Microsoft Copilot governance (Phase 4): risk, schemas, drift."""

import pytest
from pydantic import ValidationError

from app.schemas.copilot import CopilotSyncRequest
from app.services.agentic_service import risk_band
from app.services.copilot_service import (
    CONNECTOR_TYPE_BASE_RISK,
    COPILOT_INSTANCE_BASE_RISK,
    compare_state_to_baseline,
    compute_connector_risk_score,
    compute_copilot_instance_risk_score,
)


def test_connector_risk_base_by_type() -> None:
    assert compute_connector_risk_score("custom") > compute_connector_risk_score("power_platform")
    assert compute_connector_risk_score("power_platform") > compute_connector_risk_score("graph")
    assert compute_connector_risk_score("graph") == CONNECTOR_TYPE_BASE_RISK["graph"]


def test_connector_risk_sensitive_scope_increases() -> None:
    base = compute_connector_risk_score("graph")
    with_sensitive = compute_connector_risk_score("graph", scopes=["pii.read"])
    assert with_sensitive > base


def test_connector_risk_broad_permissions_increase() -> None:
    base = compute_connector_risk_score("graph")
    with_broad = compute_connector_risk_score("graph", permissions=["admin"])
    assert with_broad > base


def test_connector_risk_risky_auth_increases() -> None:
    base = compute_connector_risk_score("graph", auth_type="oauth")
    with_api_key = compute_connector_risk_score("graph", auth_type="api_key")
    assert with_api_key > base


def test_connector_risk_is_bounded_and_deterministic() -> None:
    kwargs = {
        "connector_type": "custom",
        "auth_type": "api_key",
        "scopes": ["mail.readwrite", "files.readwrite"],
        "data_sources": ["pii"],
        "permissions": ["admin", "write"],
    }
    score = compute_connector_risk_score(**kwargs)
    assert 0 <= score <= 100
    assert compute_connector_risk_score(**kwargs) == score


def test_instance_risk_base_by_type() -> None:
    assert compute_copilot_instance_risk_score("copilot_studio_agent") > compute_copilot_instance_risk_score("m365_copilot")
    assert compute_copilot_instance_risk_score("m365_copilot") > compute_copilot_instance_risk_score("teams")
    assert compute_copilot_instance_risk_score("teams") == COPILOT_INSTANCE_BASE_RISK["teams"]


def test_instance_risk_sensitive_data_increases() -> None:
    base = compute_copilot_instance_risk_score("m365_copilot")
    with_sensitive = compute_copilot_instance_risk_score("m365_copilot", data_sources=["customer"])
    assert with_sensitive > base


def test_risk_band_reused() -> None:
    assert risk_band(85) == "critical"
    assert risk_band(65) == "high"
    assert risk_band(40) == "medium"
    assert risk_band(10) == "low"


def test_sync_request_accepts_instances_and_connectors() -> None:
    request = CopilotSyncRequest(
        instances=[{"external_id": "a", "name": "A"}],
        connectors=[{"external_id": "b", "name": "B"}],
    )
    assert len(request.instances) == 1
    assert len(request.connectors) == 1


def test_sync_request_defaults_empty_lists() -> None:
    request = CopilotSyncRequest()
    assert request.instances == []
    assert request.connectors == []
    assert request.audit_events == []


def _baseline_state() -> dict:
    return {
        "instances": [
            {"external_id": "i1", "name": "Copilot A", "risk_score": 30, "status": "active"},
        ],
        "connectors": [
            {"external_id": "c1", "name": "Connector A", "risk_score": 25, "status": "active"},
        ],
    }


def test_drift_detection_risk_increase() -> None:
    current = {
        "instances": [
            {"external_id": "i1", "name": "Copilot A", "risk_score": 70, "status": "active"},
        ],
        "connectors": [
            {"external_id": "c1", "name": "Connector A", "risk_score": 25, "status": "active"},
        ],
    }
    findings = compare_state_to_baseline(_baseline_state(), current)
    risk_increases = [f for f in findings if f["drift_type"] == "risk_increase"]
    assert len(risk_increases) == 1
    assert risk_increases[0]["entity_external_id"] == "i1"
    assert risk_increases[0]["severity"] == "critical"


def test_drift_detection_new_entity() -> None:
    current = {
        "instances": [
            {"external_id": "i1", "name": "Copilot A", "risk_score": 30, "status": "active"},
            {"external_id": "i2", "name": "Copilot B", "risk_score": 50, "status": "active"},
        ],
        "connectors": [
            {"external_id": "c1", "name": "Connector A", "risk_score": 25, "status": "active"},
        ],
    }
    findings = compare_state_to_baseline(_baseline_state(), current)
    new_entities = [f for f in findings if f["drift_type"] == "new_entity"]
    assert len(new_entities) == 1
    assert new_entities[0]["entity_external_id"] == "i2"


def test_drift_detection_removed_entity() -> None:
    current = {
        "instances": [],
        "connectors": [
            {"external_id": "c1", "name": "Connector A", "risk_score": 25, "status": "active"},
        ],
    }
    findings = compare_state_to_baseline(_baseline_state(), current)
    removed = [f for f in findings if f["drift_type"] == "removed_entity"]
    assert len(removed) == 1
    assert removed[0]["entity_external_id"] == "i1"


def test_drift_detection_policy_mismatch() -> None:
    current = {
        "instances": [
            {"external_id": "i1", "name": "Copilot A", "risk_score": 30, "status": "removed"},
        ],
        "connectors": [
            {"external_id": "c1", "name": "Connector A", "risk_score": 25, "status": "active"},
        ],
    }
    findings = compare_state_to_baseline(_baseline_state(), current)
    mismatches = [f for f in findings if f["drift_type"] == "policy_mismatch"]
    assert len(mismatches) == 1
    assert mismatches[0]["entity_external_id"] == "i1"


def test_drift_detection_no_change() -> None:
    findings = compare_state_to_baseline(_baseline_state(), _baseline_state())
    assert findings == []
