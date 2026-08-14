"""PII detection, classification, and redaction pipeline for the Data Protection module."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.dlp_classification import derive_sensitivity_labels, highest_sensitivity

SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
US_PHONE_PATTERN = re.compile(r"\b\d{3}-\d{3}-\d{4}\b")
EU_ID_PATTERN = re.compile(r"\b[A-Z]{2}\d{6,12}\b")
PHI_PATTERN = re.compile(r"\b(?:patient|diagnosis|treatment|medical record|medical history|mrn)\b", re.IGNORECASE)
PCI_CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")
FINANCIAL_PATTERN = re.compile(
    r"\b(?:bank account|account number|routing number|iban|swift|sort code|credit score)\b", re.IGNORECASE
)

CLASSIFIERS: list[tuple[str, re.Pattern[str]]] = [
    ("SSN", SSN_PATTERN),
    ("Email", EMAIL_PATTERN),
    ("US Phone", US_PHONE_PATTERN),
    ("EU Personal ID", EU_ID_PATTERN),
    ("PHI", PHI_PATTERN),
    ("PCI Card", PCI_CARD_PATTERN),
    ("Financial Account", FINANCIAL_PATTERN),
]


@dataclass
class DlpScanResult:
    classifications: list[str] = field(default_factory=list)
    sensitivity_labels: list[str] = field(default_factory=list)
    highest_sensitivity: str | None = None
    has_pii: bool = False
    region: str = "US"
    redacted_content: str | None = None
    match_count: int = 0


def scan_content(content: str, *, region: str = "US") -> DlpScanResult:
    """Detect PII types and redact known patterns before downstream policy evaluation."""
    labels: list[str] = []
    redacted = content
    match_count = 0

    for label, pattern in CLASSIFIERS:
        matches = pattern.findall(content)
        if matches:
            labels.append(label)
            match_count += len(matches)
            redacted = pattern.sub("[REDACTED]", redacted)

    sensitivity_labels = derive_sensitivity_labels(labels)
    return DlpScanResult(
        classifications=labels,
        sensitivity_labels=sensitivity_labels,
        highest_sensitivity=highest_sensitivity(sensitivity_labels),
        has_pii=bool(labels),
        region=region,
        redacted_content=redacted if redacted != content else None,
        match_count=match_count,
    )


def infer_region_from_bundle(bundle_name: str | None) -> str:
    if not bundle_name:
        return "US"
    lower = bundle_name.lower()
    if "eu" in lower or "strict" in lower:
        return "EU"
    return "US"
