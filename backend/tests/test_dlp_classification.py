from app.services.dlp_classification import (
    derive_sensitivity_labels,
    highest_sensitivity,
)
from app.services.dlp_service import scan_content


def test_derive_sensitivity_labels_maps_entities() -> None:
    labels = derive_sensitivity_labels(["SSN", "Email", "PHI"])
    assert "RESTRICTED_PII" in labels
    assert "INTERNAL_PII" in labels
    assert "RESTRICTED_PHI" in labels


def test_highest_sensitivity_prefers_phi_over_pii() -> None:
    labels = derive_sensitivity_labels(["SSN", "PHI"])
    assert highest_sensitivity(labels) == "RESTRICTED_PHI"


def test_scan_content_includes_sensitivity_labels() -> None:
    result = scan_content("Contact john@example.com or SSN 123-45-6789")
    assert "RESTRICTED_PII" in result.sensitivity_labels
    assert "INTERNAL_PII" in result.sensitivity_labels
    assert result.highest_sensitivity == "RESTRICTED_PII"
