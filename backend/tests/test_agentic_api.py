"""Unit tests for the agent control plane risk scoring and schema contracts."""

import pytest
from pydantic import ValidationError

from app.schemas.agentic import (
    AgentPolicyResponse,
    ApprovalDecisionRequest,
    EndpointRegisterRequest,
    SecurityEventIngestRequest,
)
from app.models.governance import PolicyBundle
from app.services.agentic_service import (
    DEFAULT_FILE_GOVERNANCE_RULES,
    compute_agent_risk_score,
    file_governance_rules_for_bundle,
    risk_band,
)


def test_endpoint_register_requires_hostname() -> None:
    with pytest.raises(ValidationError):
        EndpointRegisterRequest()


def test_security_event_ingest_requires_action() -> None:
    with pytest.raises(ValidationError):
        SecurityEventIngestRequest()


def test_security_event_decision_defaults_to_log() -> None:
    event = SecurityEventIngestRequest(action="file.read")
    assert event.decision == "log"
    assert event.risk_score == 0


def test_security_event_rejects_invalid_decision() -> None:
    with pytest.raises(ValidationError):
        SecurityEventIngestRequest(action="file.read", decision="unknown")


def test_security_event_rejects_out_of_range_risk() -> None:
    with pytest.raises(ValidationError):
        SecurityEventIngestRequest(action="file.read", risk_score=101)


def test_risk_band_boundaries() -> None:
    assert risk_band(0) == "low"
    assert risk_band(29) == "low"
    assert risk_band(30) == "medium"
    assert risk_band(59) == "medium"
    assert risk_band(60) == "high"
    assert risk_band(79) == "high"
    assert risk_band(80) == "critical"
    assert risk_band(100) == "critical"


def test_risk_score_is_deterministic_and_bounded() -> None:
    first = compute_agent_risk_score("autonomous_agent", ["kubectl delete", "shell exec"], ["jira"], [".env", "~/.ssh"], ["sudo"])
    second = compute_agent_risk_score("autonomous_agent", ["kubectl delete", "shell exec"], ["jira"], [".env", "~/.ssh"], ["sudo"])
    assert first == second
    assert 0 <= first <= 100


def test_destructive_tools_increase_risk() -> None:
    base = compute_agent_risk_score("coding_agent")
    destructive = compute_agent_risk_score("coding_agent", ["kubectl delete", "terraform apply"])
    assert destructive > base


def test_sensitive_data_sources_increase_risk() -> None:
    base = compute_agent_risk_score("coding_agent")
    sensitive = compute_agent_risk_score("coding_agent", [], [], [".env", "~/.aws/credentials"])
    assert sensitive > base


def test_approval_decision_request_defaults_to_empty_reason() -> None:
    request = ApprovalDecisionRequest()
    assert request.reason == ""


def test_approval_decision_is_a_valid_ingest_decision() -> None:
    event = SecurityEventIngestRequest(action="shell.exec", decision="approval")
    assert event.decision == "approval"


def test_file_governance_defaults_apply_without_bundle() -> None:
    rules = file_governance_rules_for_bundle(None)
    assert any(rule["pattern"] == ".env" and rule["action"] == "block" for rule in rules)
    assert rules == DEFAULT_FILE_GOVERNANCE_RULES


def test_file_governance_rules_use_bundle_when_present() -> None:
    bundle = PolicyBundle(
        name="payments",
        file_governance_rules=[{"pattern": "*.pem", "classification": "*", "action": "approval"}],
    )
    rules = file_governance_rules_for_bundle(bundle)
    assert rules[0]["action"] == "approval"


def test_agent_policy_response_accepts_rules() -> None:
    response = AgentPolicyResponse(
        version="2",
        rules=[{"pattern": ".env", "classification": "*", "action": "block"}],
    )
    assert response.version == "2"
    assert response.rules[0].pattern == ".env"
