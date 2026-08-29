"""Structural AST and command syntax risk analyzer (Zero-AI).

Performs deterministic syntax parsing for SQL statements, shell commands,
code execution primitives, and MCP tool call arguments.
"""

from __future__ import annotations

import re
from typing import Any

# Dangerous SQL AST patterns
_SQL_DESTRUCTIVE_PATTERN = re.compile(
    r"\b(DROP\s+(?:TABLE|DATABASE|SCHEMA|VIEW|INDEX|PROCEDURE|FUNCTION|TRIGGER)|"
    r"TRUNCATE\s+(?:TABLE\s+)?[a-zA-Z0-9_.\"']+|"
    r"ALTER\s+(?:TABLE|DATABASE)\s+[a-zA-Z0-9_.\"']+\s+DROP|"
    r"DELETE\s+FROM\s+[a-zA-Z0-9_.\"']+\s*(?:;\s*$|WHERE\s+1\s*=\s*1)|"
    r"GRANT\s+ALL\s+PRIVILEGES|XP_CMDSHELL|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b",
    re.IGNORECASE,
)

# Dangerous Shell & System Command patterns
_SHELL_DESTRUCTIVE_PATTERN = re.compile(
    r"(?:\b(rm\s+-[rRfF]{1,3}\s+[/~*]|rmdir\s+/[sS]|mkfs(?:\.[a-z0-9]+)?\s+|dd\s+if=.*of=/dev/|"
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:|"  # Fork bomb
    r"curl\s+[^|\n]+(?:\|\s*(?:bash|sh|zsh|python|perl))|"
    r"wget\s+[^|\n]+(?:\|\s*(?:bash|sh|zsh|python|perl))|"
    r"chmod\s+(?:-R\s+)?777\s+[/~*]|chown\s+-R\s+root\s+|"
    r"iptables\s+-F|ufw\s+disable|systemctl\s+stop\s+(?:firewalld|auditd|sshd)|"
    r"kill\s+-9\s+(?:-1|1)\b))",
    re.IGNORECASE,
)

# Dangerous Code Execution primitives (Python, Node.js, Ruby, PHP)
_CODE_EXEC_PATTERN = re.compile(
    r"\b(__import__\s*\(\s*['\"]os['\"]\s*\)|"
    r"os\.system\s*\(|subprocess\.(?:Popen|run|call|check_output)\s*\(|"
    r"eval\s*\([^)]+\)|exec\s*\([^)]+\)|child_process\.(?:exec|spawn|execSync)\s*\(|"
    r"fs\.(?:unlinkSync|rmdirSync|rmSync)\s*\(|passthru\s*\(|shell_exec\s*\()\b",
    re.IGNORECASE,
)

# System credential exfiltration patterns (.env, AWS secrets, id_rsa, /etc/shadow)
_EXFILTRATION_TARGET_PATTERN = re.compile(
    r"(?:/etc/(?:passwd|shadow)|~/\.ssh/(?:id_rsa|id_ed25519|authorized_keys)|"
    r"\.env(?:\.(?:production|local|prod))?|~/\.aws/(?:credentials|config)|"
    r"/var/run/secrets/kubernetes\.io/serviceaccount/token|id_rsa\.pub)",
    re.IGNORECASE,
)


def analyze_syntax_risk(text: str) -> list[dict[str, Any]]:
    """
    Analyzes canonicalized text for high-risk syntax structures:
    - SQL DDL/DML destructive drops
    - Dangerous OS shell commands
    - Code execution primitives
    - Sensitive filesystem exfiltration targets
    """
    if not text:
        return []

    findings: list[dict[str, Any]] = []

    # 1. Check SQL Destructive commands
    for match in _SQL_DESTRUCTIVE_PATTERN.finditer(text):
        findings.append({
            "category": "sql_destructive",
            "risk_level": "critical",
            "matched_token": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "detail": f"Destructive SQL command detected: '{match.group(0)}'",
        })

    # 2. Check Dangerous Shell commands
    for match in _SHELL_DESTRUCTIVE_PATTERN.finditer(text):
        findings.append({
            "category": "shell_destructive",
            "risk_level": "critical",
            "matched_token": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "detail": f"Dangerous system command detected: '{match.group(0)}'",
        })

    # 3. Check Code Execution primitives
    for match in _CODE_EXEC_PATTERN.finditer(text):
        findings.append({
            "category": "code_execution",
            "risk_level": "high",
            "matched_token": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "detail": f"Dynamic code execution primitive detected: '{match.group(0)}'",
        })

    # 4. Check Exfiltration Targets
    for match in _EXFILTRATION_TARGET_PATTERN.finditer(text):
        findings.append({
            "category": "credential_exfiltration",
            "risk_level": "high",
            "matched_token": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "detail": f"Sensitive file or credential target referenced: '{match.group(0)}'",
        })

    return findings


def analyze_mcp_tool_arguments(tool_name: str, arguments: dict[str, Any] | None) -> list[dict[str, Any]]:
    """
    Deeply inspects Model Context Protocol (MCP) tool invocation parameters for structural risks.
    """
    if not arguments or not isinstance(arguments, dict):
        return []

    findings: list[dict[str, Any]] = []
    t_name_lower = tool_name.lower()

    # Convert all string arguments to a combined inspectable text
    combined_values: list[str] = []
    for k, v in arguments.items():
        if isinstance(v, str):
            combined_values.append(v)
        elif isinstance(v, (list, dict)):
            combined_values.append(str(v))

    combined_text = " \n ".join(combined_values)
    syntax_risks = analyze_syntax_risk(combined_text)

    for risk in syntax_risks:
        risk["detail"] = f"MCP tool '{tool_name}' argument contained: {risk['detail']}"
        findings.append(risk)

    # Specific tool name risk triggers
    if any(term in t_name_lower for term in ["delete", "remove", "drop", "truncate", "purge", "destroy"]):
        if not any(f.get("risk_level") == "critical" for f in findings):
            findings.append({
                "category": "mcp_destructive_tool",
                "risk_level": "high",
                "matched_token": tool_name,
                "start": 0,
                "end": len(tool_name),
                "detail": f"MCP tool '{tool_name}' performs destructive state modifications.",
            })

    return findings
