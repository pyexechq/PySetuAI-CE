from app.services.data_protection_service import split_residency_records
from app.services.dlp_service import scan_content


def test_split_residency_records_when_both_regions_active() -> None:
    eu_records, us_records = split_residency_records(30, has_eu=True, has_us=True)
    assert eu_records == 19
    assert us_records == 11


def test_split_residency_records_eu_only() -> None:
    eu_records, us_records = split_residency_records(12, has_eu=True, has_us=False)
    assert eu_records == 12
    assert us_records == 0


def test_split_residency_records_us_only() -> None:
    eu_records, us_records = split_residency_records(8, has_eu=False, has_us=True)
    assert eu_records == 0
    assert us_records == 8


def test_scan_content_detects_phi_pci_and_financial_data() -> None:
    result = scan_content(
        "Patient diagnosis: asthma. Card 4111 1111 1111 1111. Bank account number 12345."
    )

    assert result.has_pii is True
    assert {"PHI", "PCI Card", "Financial Account"}.issubset(result.classifications)
    assert "RESTRICTED_PHI" in result.sensitivity_labels
    assert "RESTRICTED_PCI" in result.sensitivity_labels
    assert result.match_count >= 3
    assert result.redacted_content is not None
    assert "diagnosis" not in result.redacted_content.lower()


def test_scan_content_keeps_benign_financial_language() -> None:
    result = scan_content("Review the financial forecast for next quarter.")

    assert result.has_pii is False
    assert result.classifications == []
