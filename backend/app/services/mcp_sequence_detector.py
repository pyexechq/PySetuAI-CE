"""Deterministic Sequential MCP Tool Chain Attack Detection Engine.

Analyzes autonomous agent tool execution sequences across iteration loops
to intercept multi-step exfiltration, code execution, destructive mutations,
and runaway infinite loops before tool execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


# Tool taxonomy classification categories
READ_SENSITIVE_TOOLS = {
    "read_file", "get_secret", "fetch_credentials", "dump_table", "query_sql",
    "cat_file", "download_file", "get_env", "read_key", "access_token",
    "read_database", "fetch_pii", "dump_secrets", "export_data", "view_file"
}

NETWORK_EGRESS_TOOLS = {
    "http_post", "send_webhook", "curl", "fetch_url", "send_email",
    "post_message", "upload_file", "http_request", "request_post",
    "send_slack_message", "send_teams_message", "external_api_call"
}

CODE_EXEC_TOOLS = {
    "bash_exec", "shell_command", "eval", "run_code", "execute_script",
    "subprocess", "spawn_process", "terminal_cmd", "run_command", "exec_cmd"
}

INFRA_MUTATION_TOOLS = {
    "drop_table", "delete_bucket", "terminate_instance", "truncate_table",
    "rmdir", "destroy_infra", "purge_data", "delete_database", "delete_vm"
}

INFRA_DISCOVERY_TOOLS = {
    "list_instances", "describe_clusters", "get_iam_policy", "scan_ports",
    "list_databases", "list_tables", "get_cloud_resources", "describe_infra"
}

IAM_PRIVILEGE_TOOLS = {
    "grant_admin", "attach_policy", "create_user", "update_permissions",
    "modify_iam_role", "escalate_privilege", "add_sudo_user"
}

# Declarative metadata for Edge mesh sync and compliance exports
SEQUENCE_ATTACK_PATTERNS = [
    {
        "id": "SEQ-EXFIL-001",
        "name": "Multi-Step Data Exfiltration Chain",
        "attack_pattern": "EXFILTRATION_CHAIN",
        "source_category": "read_sensitive",
        "target_category": "network_egress",
        "action": "block",
        "risk_score": 95,
        "explanation": "Autonomous agent read sensitive data/secrets and immediately attempted outbound network egress.",
    },
    {
        "id": "SEQ-RCE-001",
        "name": "Remote Code Execution & Script Staging",
        "attack_pattern": "REMOTE_CODE_EXEC_CHAIN",
        "source_category": "read_sensitive",
        "target_category": "code_exec",
        "action": "block",
        "risk_score": 90,
        "explanation": "Autonomous agent accessed file system / scripts followed immediately by terminal / shell command execution.",
    },
    {
        "id": "SEQ-MUTATE-001",
        "name": "Discovery-to-Destructive Mutation Chain",
        "attack_pattern": "DESTRUCTIVE_MUTATION_CHAIN",
        "source_category": "infra_discovery",
        "target_category": "infra_mutation",
        "action": "request_approval",
        "risk_score": 85,
        "explanation": "Autonomous agent performed infrastructure discovery followed by destructive resource deletion.",
    },
    {
        "id": "SEQ-PRIVESC-001",
        "name": "Privilege Escalation Chain",
        "attack_pattern": "PRIVILEGE_ESCALATION_CHAIN",
        "source_category": "infra_discovery",
        "target_category": "iam_privilege",
        "action": "request_approval",
        "risk_score": 80,
        "explanation": "Autonomous agent probed IAM policies followed by elevated role / admin permission grant.",
    },
    {
        "id": "SEQ-LOOP-001",
        "name": "Runaway Agent Infinite Loop Breaker",
        "attack_pattern": "RUNAWAY_LOOP",
        "source_category": "identical_call",
        "target_category": "identical_call",
        "action": "block",
        "risk_score": 70,
        "explanation": "Agent triggered 3 identical consecutive tool calls with identical arguments.",
    },
]


@dataclass
class ToolSequenceVerdict:
    is_threat: bool
    attack_pattern: str | None
    action: str  # allow | block | request_approval
    risk_score: int
    risk_tier: str
    reason: str
    chain_length: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_threat": self.is_threat,
            "attack_pattern": self.attack_pattern,
            "action": self.action,
            "risk_score": self.risk_score,
            "risk_tier": self.risk_tier,
            "reason": self.reason,
            "chain_length": self.chain_length,
        }


def _classify_tool(tool_name: str) -> set[str]:
    """Tag a tool name with its operational capability categories."""
    lowered = tool_name.strip().lower()
    categories = set()

    for category, tool_set in (
        ("read_sensitive", READ_SENSITIVE_TOOLS),
        ("network_egress", NETWORK_EGRESS_TOOLS),
        ("code_exec", CODE_EXEC_TOOLS),
        ("infra_mutation", INFRA_MUTATION_TOOLS),
        ("infra_discovery", INFRA_DISCOVERY_TOOLS),
        ("iam_privilege", IAM_PRIVILEGE_TOOLS),
    ):
        if any(keyword in lowered for keyword in tool_set) or lowered in tool_set:
            categories.add(category)

    return categories


def evaluate_tool_sequence(
    tool_history: list[dict[str, Any]],
    current_tool: str,
    current_args: dict[str, Any] | None = None,
) -> ToolSequenceVerdict:
    """Evaluate multi-step tool call sequence history against deterministic attack patterns."""
    current_args = current_args or {}
    chain_length = len(tool_history) + 1
    curr_cats = _classify_tool(current_tool)

    # 1. Runaway Infinite Loop Check (Identical Tool + Arguments Repeated >= 3 times)
    if len(tool_history) >= 2:
        recent = tool_history[-2:]
        if all(
            step.get("name") == current_tool and step.get("arguments") == current_args
            for step in recent
        ):
            return ToolSequenceVerdict(
                is_threat=True,
                attack_pattern="RUNAWAY_LOOP",
                action="block",
                risk_score=70,
                risk_tier="HIGH",
                reason=f"Detected repetitive infinite loop: tool '{current_tool}' invoked 3 consecutive times with identical arguments.",
                chain_length=chain_length,
            )

    # Prior tool categorization
    prior_tools = [step.get("name", "") for step in tool_history]
    prior_categories = set()
    for t in prior_tools:
        prior_categories.update(_classify_tool(t))

    # 2. Exfiltration Chain: [Read Sensitive Storage] -> [Network Egress]
    if "read_sensitive" in prior_categories and "network_egress" in curr_cats:
        return ToolSequenceVerdict(
            is_threat=True,
            attack_pattern="EXFILTRATION_CHAIN",
            action="block",
            risk_score=95,
            risk_tier="CRITICAL",
            reason=f"Sequential exfiltration pattern detected: sensitive data read ({', '.join(prior_tools)}) followed by outbound network egress ('{current_tool}').",
            chain_length=chain_length,
        )

    # 3. Remote Code Execution Chain: [Download/Write File] -> [Bash Exec/Eval]
    if "read_sensitive" in prior_categories and "code_exec" in curr_cats:
        return ToolSequenceVerdict(
            is_threat=True,
            attack_pattern="REMOTE_CODE_EXEC_CHAIN",
            action="block",
            risk_score=90,
            risk_tier="CRITICAL",
            reason=f"Sequential code execution chain detected: local file/secret read followed by direct command execution ('{current_tool}').",
            chain_length=chain_length,
        )

    # 4. Destructive Mutation Chain: [Infra Discovery] -> [Destructive Deletion]
    if "infra_discovery" in prior_categories and "infra_mutation" in curr_cats:
        return ToolSequenceVerdict(
            is_threat=True,
            attack_pattern="DESTRUCTIVE_MUTATION_CHAIN",
            action="request_approval",
            risk_score=85,
            risk_tier="HIGH",
            reason=f"Destructive mutation sequence detected: infrastructure discovery followed by destructive action ('{current_tool}'). Human authorization required.",
            chain_length=chain_length,
        )

    # 5. Privilege Escalation Chain: [IAM Discovery] -> [Modify Permissions/Roles]
    if "infra_discovery" in prior_categories and "iam_privilege" in curr_cats:
        return ToolSequenceVerdict(
            is_threat=True,
            attack_pattern="PRIVILEGE_ESCALATION_CHAIN",
            action="request_approval",
            risk_score=80,
            risk_tier="HIGH",
            reason=f"Privilege escalation sequence detected: IAM enumeration followed by permission modification ('{current_tool}'). Human authorization required.",
            chain_length=chain_length,
        )

    # Direct Single-Step High-Risk Fallback
    if "infra_mutation" in curr_cats:
        return ToolSequenceVerdict(
            is_threat=True,
            attack_pattern="DIRECT_DESTRUCTIVE_MUTATION",
            action="request_approval",
            risk_score=75,
            risk_tier="HIGH",
            reason=f"Destructive tool invocation ('{current_tool}') requires human approval.",
            chain_length=chain_length,
        )

    return ToolSequenceVerdict(
        is_threat=False,
        attack_pattern=None,
        action="allow",
        risk_score=10,
        risk_tier="LOW",
        reason="Safe tool execution sequence.",
        chain_length=chain_length,
    )
