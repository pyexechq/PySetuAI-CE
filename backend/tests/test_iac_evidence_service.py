"""Tests for IaC evidence config and tenant-aware scanning."""

from pathlib import Path

import pytest

from app.services.iac_evidence_config_service import _normalize_checks, _normalize_scan_paths
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


def test_normalize_scan_paths_rejects_empty() -> None:
    with pytest.raises(ValueError):
        _normalize_scan_paths([])


def test_normalize_checks_requires_pattern() -> None:
    with pytest.raises(ValueError):
        _normalize_checks([{"id": "X", "title": "Test", "framework": "SOC", "pattern": ""}])
