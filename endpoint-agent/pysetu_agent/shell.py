"""Shell command governance for the endpoint agent.

Classifies shell commands into allow / approval / block using an ordered
rule list. Block rules are checked first, then approval, then allow by
default. This is a heuristic pre-filter, not a full shell sandbox.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ShellDecision:
    action: str
    reason: str


_BLOCK_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brm\s+[^\n]*(?:-rf|-fr)\b[^\n]*(?:\s/|\s~|\s\*)"), "Destructive recursive delete"),
    (re.compile(r"\bchmod\s+(?:-R\s+)?777\b"), "World-writable permissions"),
    (re.compile(r"\b(?:curl|wget)\b[^\n]*\b(?:token|secret|api[_-]?key|password|credential)\b"), "Potential data exfiltration"),
    (re.compile(r"\bcat\s+~?/\.ssh/id_(?:rsa|ed25519|ecdsa)\b"), "Private key access"),
    (re.compile(r"\bgit\s+push\b.*--force"), "Force push to remote"),
    (re.compile(r"\bfind\b[^\n]*\b-delete\b"), "Bulk file deletion"),
]

_APPROVAL_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgit\s+push\b"), "Push to remote"),
    (re.compile(r"\bdocker\s+exec\b"), "Container exec"),
    (re.compile(r"\bkubectl\s+delete\b"), "Kubernetes resource deletion"),
    (re.compile(r"\bterraform\s+apply\b"), "Infrastructure apply"),
    (re.compile(r"\bchmod\b"), "Permission change"),
    (re.compile(r"\bsudo\b"), "Elevated privileges"),
    (re.compile(r"\brm\s+-(?:rf|fr)\b"), "Recursive delete"),
    (re.compile(r"\b(?:shutdown|reboot|dropdb)\b"), "Destructive system action"),
]


def classify_command(command: str) -> ShellDecision:
    for pattern, reason in _BLOCK_RULES:
        if pattern.search(command):
            return ShellDecision(action="block", reason=reason)
    for pattern, reason in _APPROVAL_RULES:
        if pattern.search(command):
            return ShellDecision(action="approval", reason=reason)
    return ShellDecision(action="allow", reason="No risky pattern matched")
