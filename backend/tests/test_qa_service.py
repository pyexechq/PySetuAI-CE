from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.qa_service import (
    _parse_pytest_output,
    guidance_for_case,
    run_automated_tests,
)
from app.services.qa_test_catalog import TEST_CASE_CATALOG


def test_test_case_catalog_has_unique_ids() -> None:
    ids = [item.case_id for item in TEST_CASE_CATALOG]
    assert len(ids) == len(set(ids))


def test_test_case_catalog_covers_core_modules() -> None:
    modules = {item.module for item in TEST_CASE_CATALOG}
    for expected in ("Dashboard", "Security Center", "MCP Governance", "Multi-Tenant"):
        assert expected in modules


def test_guidance_for_known_failure_case() -> None:
    guidance = guidance_for_case("MCP-005")
    assert guidance["linked_defect_code"] == "DEF-001"
    assert "policy engine" in (guidance["remediation_hint"] or "").lower()


def test_parse_pytest_output() -> None:
    output = """
tests/test_rate_limit.py::test_auth_rate_limit_paths_include_login PASSED
tests/test_security_scan.py::test_security_scan_detects_injection FAILED
"""
    parsed = _parse_pytest_output(output)
    assert parsed["tests/test_rate_limit.py::test_auth_rate_limit_paths_include_login"] == "pass"
    assert parsed["tests/test_security_scan.py::test_security_scan_detects_injection"] == "fail"


def test_run_automated_retest_failed_only_targets_failed_keys() -> None:
    import asyncio

    user = SimpleNamespace(name="QA User", email="qa@example.com")
    failed_case = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        automated_key="tests/test_security_scan.py::test_security_scan_detects_injection",
        status="fail",
    )
    pass_case = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000002",
        automated_key="tests/test_rate_limit.py::test_auth_rate_limit_paths_include_login",
        status="pass",
    )

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "tests/test_security_scan.py::test_security_scan_detects_injection PASSED\n"
    mock_proc.stderr = ""

    db = MagicMock()
    db.commit = AsyncMock(return_value=None)

    with patch("app.services.qa_service.get_cycle", return_value=(SimpleNamespace(), [failed_case, pass_case])):
        with patch("app.services.qa_service._execute_pytest", return_value=mock_proc) as mock_exec:
            result = asyncio.run(
                run_automated_tests(
                    db,
                    tenant_id="00000000-0000-0000-0000-000000000099",
                    cycle_id="00000000-0000-0000-0000-000000000010",
                    user=user,
                    scope="failed",
                )
            )

    mock_exec.assert_called_once()
    called_targets = mock_exec.call_args[0][0]
    assert called_targets == ["tests/test_security_scan.py::test_security_scan_detects_injection"]
    assert result["scope"] == "failed"
    assert result["cases_updated"] == 1
    assert failed_case.status == "pass"
