"""Static IaC evidence scanner for deployment manifests (Checkov-style heuristics)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

DEPLOY_ROOT = Path(__file__).resolve().parents[3] / "deploy"

CONTROL_CHECKS: list[dict[str, str]] = [
    {
        "id": "IAC-OPA-001",
        "title": "OPA policy agent deployed",
        "framework": "ISO 27001 A.8.9",
        "pattern": "opa",
    },
    {
        "id": "IAC-GW-001",
        "title": "Gateway data-movement Rego policies present",
        "framework": "ISO 27001 A.8.11",
        "pattern": "restricted_data_movement",
    },
    {
        "id": "IAC-SEC-001",
        "title": "Kubernetes secrets not inlined in templates",
        "framework": "SOC 2 CC6.1",
        "pattern": "secretKeyRef",
    },
    {
        "id": "IAC-SEC-002",
        "title": "Resource limits configured for workloads",
        "framework": "ISO 27001 A.8.6",
        "pattern": "resources:",
    },
    {
        "id": "IAC-NET-001",
        "title": "Ingress TLS termination configured",
        "framework": "PCI DSS 4.1",
        "pattern": "tls",
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


def _scan_paths() -> list[Path]:
    paths: list[Path] = []
    for relative in (
        "helm/pysetu/templates",
        "helm/pysetu/values.yaml",
        "helm/pysetu/files",
        "opa/policies",
    ):
        target = DEPLOY_ROOT / relative
        if target.is_file():
            paths.append(target)
        elif target.is_dir():
            paths.extend(sorted(target.rglob("*")))
    return [path for path in paths if path.is_file() and path.suffix in {".yaml", ".yml", ".rego", ".tpl"}]


def run_iac_evidence_scan(*, deploy_root: Path | None = None) -> dict[str, Any]:
    root = deploy_root or DEPLOY_ROOT
    files = []
    for relative in (
        "helm/pysetu/templates",
        "helm/pysetu/values.yaml",
        "helm/pysetu/files",
        "opa/policies",
    ):
        target = root / relative
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(sorted(target.rglob("*")))
    files = [path for path in files if path.is_file() and path.suffix in {".yaml", ".yml", ".rego", ".tpl"}]

    contents: dict[str, str] = {}
    for path in files:
        if path.name.startswith("._"):
            continue
        try:
            contents[str(path.relative_to(root))] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

    combined = "\n".join(contents.values())
    checks: list[IacCheckResult] = []
    for spec in CONTROL_CHECKS:
        matched_files = [name for name, body in contents.items() if spec["pattern"] in body]
        if spec["id"] == "IAC-SEC-001":
            bad_files = [
                name
                for name, body in contents.items()
                if "password:" in body.lower() and "secretkeyref" not in body.lower()
            ]
            status = "pass" if not bad_files else "warn"
            detail = "No inline passwords detected" if not bad_files else f"Review inline secrets in: {', '.join(bad_files)}"
            checks.append(
                IacCheckResult(
                    id=spec["id"],
                    title=spec["title"],
                    framework=spec["framework"],
                    status=status,
                    evidence_files=matched_files or list(contents.keys())[:3],
                    detail=detail,
                )
            )
            continue

        status = "pass" if matched_files or spec["pattern"] in combined else "fail"
        checks.append(
            IacCheckResult(
                id=spec["id"],
                title=spec["title"],
                framework=spec["framework"],
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
