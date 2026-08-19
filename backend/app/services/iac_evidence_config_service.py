"""Tenant IaC evidence scanner configuration."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.iac_evidence_service import (
    DEFAULT_CONTROL_CHECKS,
    DEFAULT_SCAN_PATHS,
    resolve_deploy_root,
    run_iac_evidence_scan,
)
from app.services.integration_service import get_or_create_integration


def _normalize_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for item in checks:
        check_id = str(item.get("id", "")).strip()
        if not check_id or check_id in seen:
            continue
        seen.add(check_id)
        pattern = str(item.get("pattern", "")).strip()
        if not pattern:
            continue
        normalized.append(
            {
                "id": check_id,
                "title": str(item.get("title", check_id)).strip() or check_id,
                "framework": str(item.get("framework", "")).strip(),
                "pattern": pattern,
                "enabled": bool(item.get("enabled", True)),
            }
        )
    if not normalized:
        raise ValueError("At least one enabled check with a pattern is required.")
    return normalized


def _normalize_scan_paths(paths: list[str]) -> list[str]:
    cleaned = [path.strip().lstrip("/") for path in paths if path and path.strip()]
    if not cleaned:
        raise ValueError("At least one scan path is required.")
    return cleaned


async def get_tenant_iac_config(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    row = await get_or_create_integration(db, tenant_id)
    deploy_root = resolve_deploy_root()
    scan_paths = row.iac_scan_paths if row.iac_scan_paths else DEFAULT_SCAN_PATHS
    checks = row.iac_checks if row.iac_checks else DEFAULT_CONTROL_CHECKS
    return {
        "deploy_root": str(deploy_root),
        "deploy_root_env": "IAC_DEPLOY_ROOT",
        "scan_paths": scan_paths,
        "checks": checks,
        "is_customized": row.iac_scan_paths is not None or row.iac_checks is not None,
        "defaults": {
            "scan_paths": DEFAULT_SCAN_PATHS,
            "checks": DEFAULT_CONTROL_CHECKS,
        },
    }


async def save_tenant_iac_config(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    scan_paths: list[str],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    row = await get_or_create_integration(db, tenant_id)
    row.iac_scan_paths = _normalize_scan_paths(scan_paths)
    row.iac_checks = _normalize_checks(checks)
    await db.commit()
    await db.refresh(row)
    return await get_tenant_iac_config(db, tenant_id)


async def reset_tenant_iac_config(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    row = await get_or_create_integration(db, tenant_id)
    row.iac_scan_paths = None
    row.iac_checks = None
    await db.commit()
    await db.refresh(row)
    return await get_tenant_iac_config(db, tenant_id)


async def run_tenant_iac_scan(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    config = await get_tenant_iac_config(db, tenant_id)
    return run_iac_evidence_scan(
        deploy_root=resolve_deploy_root(),
        scan_paths=config["scan_paths"],
        check_specs=config["checks"],
    )
