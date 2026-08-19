"""Local policy evaluation and offline cache for the endpoint agent.

Rules match resource paths against classification labels and resolve to an
action. When no rule matches, classification-based defaults apply (secrets are
blocked, PII is redacted). The cache stores a versioned, integrity-checked
snapshot so decisions continue offline.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from dataclasses import dataclass, field

ACTION_RANK = {"allow": 1, "log": 2, "redact": 3, "approval": 4, "block": 5}
CLASSIFICATION_DEFAULT_ACTION = {
    "SECRET": "block",
    "PRIVATE_KEY": "block",
    "AWS_ACCESS_KEY": "block",
    "GENERIC_SECRET": "block",
}


@dataclass(frozen=True)
class PolicyRule:
    pattern: str
    classification: str
    action: str


@dataclass
class LocalPolicy:
    rules: list[PolicyRule] = field(default_factory=list)
    version: str = "1"

    @classmethod
    def defaults(cls) -> "LocalPolicy":
        return cls(
            rules=[
                PolicyRule(".env", "*", "block"),
                PolicyRule(".env.*", "*", "block"),
                PolicyRule("*.pem", "*", "block"),
                PolicyRule("*.key", "*", "block"),
                PolicyRule("credentials.*", "*", "block"),
                PolicyRule("~/.ssh/**", "*", "block"),
                PolicyRule("~/.aws/**", "*", "block"),
                PolicyRule("*.sql", "PII", "redact"),
                PolicyRule("src/**", "*", "allow"),
                PolicyRule("tests/**", "*", "allow"),
            ]
        )


def expand_home(path: str) -> str:
    return os.path.expanduser(path)


def path_matches(pattern: str, resource: str) -> bool:
    pat = expand_home(pattern).replace("\\", "/").strip("/")
    res = expand_home(resource).replace("\\", "/").strip("/")

    candidates = [res, os.path.basename(res)]
    parts = res.split("/")
    for index in range(1, len(parts)):
        candidates.append("/".join(parts[index:]))

    for candidate in candidates:
        if fnmatch.fnmatch(candidate, pat):
            return True

    if pat.endswith("/**"):
        prefix = pat[:-3]
        return any(candidate == prefix or candidate.startswith(prefix + "/") for candidate in candidates)

    return False


def default_action_for(classifications: list[str]) -> str:
    for classification in classifications:
        if classification in CLASSIFICATION_DEFAULT_ACTION:
            return CLASSIFICATION_DEFAULT_ACTION[classification]
    if any(label in {"SSN", "EMAIL", "US_PHONE", "EU_PERSONAL_ID", "PCI_CARD"} for label in classifications):
        return "redact"
    return "allow"


def evaluate(policy: LocalPolicy, resource: str, classifications: list[str]) -> str:
    best_rank = 0
    best_action = "allow"
    for rule in policy.rules:
        classification_match = rule.classification == "*" or rule.classification in classifications
        if classification_match and path_matches(rule.pattern, resource):
            rank = ACTION_RANK.get(rule.action, 1)
            if rank > best_rank:
                best_rank = rank
                best_action = rule.action
    if best_rank > 0:
        return best_action
    return default_action_for(classifications)


def policy_from_payload(payload: dict) -> LocalPolicy:
    """Build a LocalPolicy from a control-plane policy response."""
    rules = [
        PolicyRule(
            pattern=str(rule.get("pattern", "")),
            classification=str(rule.get("classification", "*")),
            action=str(rule.get("action", "allow")),
        )
        for rule in payload.get("rules", [])
        if isinstance(rule, dict) and rule.get("pattern")
    ]
    return LocalPolicy(rules=rules, version=str(payload.get("version", "1")))


class PolicyCache:
    """File-backed policy snapshot with a SHA-256 integrity checksum."""

    def __init__(self, path: str) -> None:
        self.path = path

    def _checksum(self, rules: list[dict]) -> str:
        payload = json.dumps(sorted(rules, key=lambda rule: (rule["pattern"], rule["classification"], rule["action"])), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, policy: LocalPolicy) -> None:
        rules = [{"pattern": r.pattern, "classification": r.classification, "action": r.action} for r in policy.rules]
        document = {
            "version": policy.version,
            "checksum": self._checksum(rules),
            "rules": rules,
        }
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2)

    def load(self) -> LocalPolicy:
        with open(self.path, encoding="utf-8") as handle:
            document = json.load(handle)
        rules_raw = document.get("rules", [])
        if self._checksum(rules_raw) != document.get("checksum"):
            raise ValueError("Policy cache integrity check failed")
        rules = [
            PolicyRule(pattern=r["pattern"], classification=r["classification"], action=r["action"])
            for r in rules_raw
        ]
        return LocalPolicy(rules=rules, version=str(document.get("version", "1")))

    def load_or_defaults(self) -> LocalPolicy:
        try:
            return self.load()
        except (OSError, ValueError, KeyError):
            return LocalPolicy.defaults()
