"""Local secret and PII detection for the endpoint agent.

Portable, standard-library-only classifier that mirrors the classification
taxonomy used by the PySetu control plane DLP engine. Detections return a
redacted copy; no raw content is uploaded by the daemon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PRIVATE) PRIVATE KEY-----")),
    ("AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("OPENAI_KEY", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("GENERIC_SECRET", re.compile(r"\b(?:password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*[\"']?[^\s\"']+", re.IGNORECASE)),
]

PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("US_PHONE", re.compile(r"\b\d{3}-\d{3}-\d{4}\b")),
    ("EU_PERSONAL_ID", re.compile(r"\b[A-Z]{2}\d{6,12}\b")),
    ("PCI_CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
]

REDACTION = "[REDACTED]"


@dataclass
class ScanResult:
    classifications: list[str] = field(default_factory=list)
    redacted_content: str | None = None
    match_count: int = 0

    @property
    def has_sensitive(self) -> bool:
        return bool(self.classifications)


def detect(content: str, *, limit: int = 1_000_000) -> ScanResult:
    """Detect secrets and PII in text content and return a redacted copy."""
    if len(content) > limit:
        content = content[:limit]

    classifications: list[str] = []
    redacted = content
    match_count = 0

    for label, pattern in [*SECRET_PATTERNS, *PII_PATTERNS]:
        matches = pattern.findall(content)
        if matches:
            classifications.append(label)
            match_count += len(matches)
            redacted = pattern.sub(REDACTION, redacted)

    return ScanResult(
        classifications=classifications,
        redacted_content=redacted if redacted != content else None,
        match_count=match_count,
    )
