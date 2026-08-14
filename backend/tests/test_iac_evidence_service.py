"""Tests for static IaC evidence scanner."""

from pathlib import Path

from app.services.iac_evidence_service import run_iac_evidence_scan


def test_run_iac_evidence_scan_returns_checks() -> None:
    deploy_root = Path(__file__).resolve().parents[2] / "deploy"
    report = run_iac_evidence_scan(deploy_root=deploy_root)
    assert report["files_scanned"] > 0
    assert report["checks"]
    assert "score" in report
    check_ids = {check["id"] for check in report["checks"]}
    assert "IAC-OPA-001" in check_ids
    assert "IAC-GW-001" in check_ids
