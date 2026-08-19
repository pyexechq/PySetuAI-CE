"""Unit tests for MCP governance depth (Phase 3): tool policies and tool-chain risk."""

import pytest
from pydantic import ValidationError

from app.schemas.mcp_governance import MCPToolPolicyUpsertRequest
from app.services.mcp_tool_chain_service import (
    TOOL_RISK_BASE,
    compute_chain_risk_score,
)
from app.services.mcp_tool_policy_service import ALLOWED_ACTIONS


def test_tool_policy_requires_server_and_tool() -> None:
    with pytest.raises(ValidationError):
        MCPToolPolicyUpsertRequest()


def test_tool_policy_action_defaults_to_allow() -> None:
    policy = MCPToolPolicyUpsertRequest(server_id="00000000-0000-0000-0000-000000000001", tool_name="searchJira")
    assert policy.action == "allow"
    assert policy.risk_score == 0


def test_tool_policy_rejects_invalid_action() -> None:
    with pytest.raises(ValidationError):
        MCPToolPolicyUpsertRequest(
            server_id="00000000-0000-0000-0000-000000000001",
            tool_name="searchJira",
            action="maybe",
        )


def test_tool_policy_rejects_out_of_range_risk() -> None:
    with pytest.raises(ValidationError):
        MCPToolPolicyUpsertRequest(
            server_id="00000000-0000-0000-0000-000000000001",
            tool_name="searchJira",
            risk_score=101,
        )


def test_allowed_actions_are_allow_approval_block() -> None:
    assert ALLOWED_ACTIONS == {"allow", "approval", "block"}


def test_chain_risk_base_by_tool_risk() -> None:
    assert compute_chain_risk_score("read") == TOOL_RISK_BASE["read"]
    assert compute_chain_risk_score("write") == TOOL_RISK_BASE["write"]
    assert compute_chain_risk_score("destructive") == TOOL_RISK_BASE["destructive"]


def test_chain_risk_sensitive_data_source_increases_score() -> None:
    base = compute_chain_risk_score("read")
    with_secret = compute_chain_risk_score("read", data_source="~/.ssh/id_rsa")
    assert with_secret > base


def test_chain_risk_unknown_external_service_increases_score() -> None:
    base = compute_chain_risk_score("read")
    with_unknown = compute_chain_risk_score("read", external_service="https://random.example.com")
    assert with_unknown > base


def test_chain_risk_trusted_external_service_does_not_increase() -> None:
    base = compute_chain_risk_score("read")
    with_trusted = compute_chain_risk_score("read", external_service="github")
    assert with_trusted == base


def test_chain_risk_is_bounded_to_100() -> None:
    score = compute_chain_risk_score(
        "destructive",
        data_source="~/.ssh/id_rsa",
        external_service="https://random.example.com",
        agent_risk=100,
        mcp_server_risk=10.0,
    )
    assert 0 <= score <= 100


def test_chain_risk_is_deterministic() -> None:
    kwargs = {
        "tool_risk": "write",
        "data_source": "~/.ssh",
        "external_service": "https://random.example.com",
        "agent_risk": 40,
        "mcp_server_risk": 5.0,
    }
    assert compute_chain_risk_score(**kwargs) == compute_chain_risk_score(**kwargs)
