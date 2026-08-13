"""Shared date-range helpers (BL-094)."""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.core.date_range import resolve_range


def test_resolve_range_defaults_to_last_seven_days() -> None:
    start, end = resolve_range(None, None)
    assert (end - start).days == 7


def test_resolve_range_from_only() -> None:
    start, end = resolve_range("2026-08-01", None)
    assert start.date() == date(2026, 8, 1)
    expected_end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    assert end == expected_end


def test_resolve_range_to_only() -> None:
    start, end = resolve_range(None, "2026-08-10")
    assert end.date() == date(2026, 8, 11)
    assert (end - start).days == 7


def test_resolve_range_invalid_format_returns_400() -> None:
    with pytest.raises(HTTPException) as exc:
        resolve_range("08-01-2026", None)
    assert exc.value.status_code == 400


def test_resolve_range_from_after_to_returns_400() -> None:
    with pytest.raises(HTTPException) as exc:
        resolve_range("2026-08-10", "2026-08-01")
    assert exc.value.status_code == 400
