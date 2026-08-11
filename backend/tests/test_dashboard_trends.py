from app.services.dashboard_service import _pct_change


def test_pct_change_growth() -> None:
    assert _pct_change(150, 100) == 50.0


def test_pct_change_decline() -> None:
    assert _pct_change(80, 100) == -20.0


def test_pct_change_from_zero_previous() -> None:
    assert _pct_change(10, 0) == 100.0
    assert _pct_change(0, 0) == 0.0
