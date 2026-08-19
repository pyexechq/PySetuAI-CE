"""Static IaC evidence scanner for deployment manifests (Checkov-style heuristics)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import settings

REPO_DEPLOY_ROOT = Path(__file__).resolve().parents[3] / "deploy"
CONTAINER_DEPLOY_ROOT = Path("/deploy")

DEFAULT_SCAN_PATHS: list[str] = [
    "helm/pysetu/templates",
    "helm/pysetu/values.yaml",
    "helm/pysetu/files",
    "opa/policies",
]

DEFAULT_CONTROL_CHECKS: list[dict[str, Any]] = [
    {
        "id": "IAC-OPA-001",
        "title": "OPA policy agent deployed",
        "framework": "ISO 27001 A.8.9",
        "pattern": "opa",
        "enabled": True,
    },
    {
        "id": "IAC-GW-001",
        "title": "Gateway data-movement Rego policies present",
        "framework": "ISO 27001 A.8.11",
        "pattern": "restricted_data_movement",
        "enabled": True,
    },
    {
        "id": "IAC-SEC-001",
        "title": "Kubernetes secrets not inlined in templates",
        "framework": "SOC 2 CC6.1",
        "pattern": "secretKeyRef",
        "enabled": True,
    },
    {
        "id": "IAC-SEC-002",
        "title": "Resource limits configured for workloads",
        "framework": "ISO 27001 A.8.6",
        "pattern": "resources:",
        "enabled": True,
    },
    {
        "id": "IAC-NET-001",
        "title": "Ingress TLS termination configured",
        "framework": "PCI DSS 4.1",
        "pattern": "tls",
        "enabled": True,
    },
]


@dataclass
class IacCheckResult:
    id: str
    title: str
    framework: str
    status: str
    evidence_files: list[str] = field(default_factory=list)
    detail: str = ""


def resolve_deploy_root() -> Path:
    if settings.iac_deploy_root.strip():
        return Path(settings.iac_deploy_root).expanduser()
    if CONTAINER_DEPLOY_ROOT.is_dir():
        return CONTAINER_DEPLOY_ROOT
    return REPO_DEPLOY_ROOT


def _collect_manifest_files(root: Path, scan_paths: list[str]) -> dict[str, str]:
    contents: dict[str, str] = {}
    for relative in scan_paths:
        target = root / relative
        paths: list[Path] = []
        if target.is_file():
            paths.append(target)
        elif target.is_dir():
            paths.extend(sorted(target.rglob("*")))
        for path in paths:
            if not path.is_file() or path.suffix not in {".yaml", ".yml", ".rego", ".tpl"}:
                continue
            if path.name.startswith("._"):
                continue
            try:
                contents[str(path.relative_to(root))] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
    return contents


def run_iac_evidence_scan(
    *,
    deploy_root: Path | None = None,
    scan_paths: list[str] | None = None,
    check_specs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = deploy_root or resolve_deploy_root()
    paths = scan_paths or DEFAULT_SCAN_PATHS
    specs = check_specs or DEFAULT_CONTROL_CHECKS
    active_specs = [spec for spec in specs if spec.get("enabled", True)]

    contents = _collect_manifest_files(root, paths)
    combined = "\n".join(contents.values())
    checks: list[IacCheckResult] = []

    for spec in active_specs:
        pattern = str(spec.get("pattern", "")).strip()
        check_id = str(spec.get("id", "")).strip()
        title = str(spec.get("title", check_id)).strip()
        framework = str(spec.get("framework", "")).strip()

        if check_id == "IAC-SEC-001":
            bad_files = [
                name
                for name, body in contents.items()
                if "password:" in body.lower() and "secretkeyref" not in body.lower()
            ]
            status = "pass" if not bad_files else "warn"
            detail = (
                "No inline passwords detected"
                if not bad_files
                else f"Review inline secrets in: {', '.join(bad_files)}"
            )
            checks.append(
                IacCheckResult(
                    id=check_id,
                    title=title,
                    framework=framework,
                    status=status,
                    evidence_files=list(contents.keys())[:3],
                    detail=detail,
                )
            )
            continue

        matched_files = [name for name, body in contents.items() if pattern and pattern in body]
        status = "pass" if matched_files or (pattern and pattern in combined) else "fail"
        checks.append(
            IacCheckResult(
                id=check_id,
                title=title,
                framework=framework,
                status=status,
                evidence_files=matched_files,
                detail="Pattern found in deployment manifests" if status == "pass" else "Pattern not found",
            )
        )

    passed = sum(1 for check in checks if check.status == "pass")
    warned = sum(1 for check in checks if check.status == "warn")
    failed = sum(1 for check in checks if check.status == "fail")
    score = round((passed + warned * 0.5) / max(len(checks), 1) * 100, 1)

    return {
        "id": str(uuid4()),
        "generated_at": datetime.now(UTC).isoformat(),
        "scanner": "pysetu-static-iac",
        "deploy_root": str(root),
        "scan_paths": paths,
        "files_scanned": len(contents),
        "score": score,
        "summary": {"pass": passed, "warn": warned, "fail": failed},
        "checks": [
            {
                "id": check.id,
                "title": check.title,
                "framework": check.framework,
                "status": check.status,
                "evidence_files": check.evidence_files,
                "detail": check.detail,
            }
            for check in checks
        ],
    }
