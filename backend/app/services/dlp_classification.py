"""Map DLP detector labels to enterprise sensitivity tiers for OPA data-movement policy."""

from __future__ import annotations

ENTITY_TO_SENSITIVITY: dict[str, str] = {
    "SSN": "RESTRICTED_PII",
    "Email": "INTERNAL_PII",
    "US Phone": "RESTRICTED_PII",
    "EU Personal ID": "RESTRICTED_PII",
    "PHI": "RESTRICTED_PHI",
    "PCI Card": "RESTRICTED_PCI",
    "Financial Account": "CONFIDENTIAL_FINANCIAL",
}

SENSITIVITY_RANK: dict[str, int] = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "INTERNAL_PII": 2,
    "CONFIDENTIAL_FINANCIAL": 3,
    "RESTRICTED_PII": 4,
    "RESTRICTED_PHI": 5,
    "RESTRICTED_PCI": 5,
}

VECTOR_BLOCKED_LABELS: frozenset[str] = frozenset(
    {"RESTRICTED_PII", "RESTRICTED_PHI", "RESTRICTED_PCI"}
)

# PHI/PCI can never be exempted to any vector pipeline hop.
NEVER_EXEMPT_VECTOR_LABELS: frozenset[str] = frozenset({"RESTRICTED_PHI", "RESTRICTED_PCI"})


def derive_sensitivity_labels(entity_classifications: list[str]) -> list[str]:
    """Return unique sensitivity labels derived from detector entity labels."""
    seen: set[str] = set()
    labels: list[str] = []
    for entity in entity_classifications:
        label = ENTITY_TO_SENSITIVITY.get(entity)
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def highest_sensitivity(sensitivity_labels: list[str]) -> str | None:
    if not sensitivity_labels:
        return None
    return max(sensitivity_labels, key=lambda label: SENSITIVITY_RANK.get(label, 0))
