from app.services.data_protection_service import split_residency_records


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
