from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.rbac import MANAGE_POLICIES, USE_STUDIO, VIEW_AUDIT_LOGS, require_any_permission, require_permission
from app.core.security import jwt_loaded_from_vault
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.security import (
    AbacEvaluateRequest,
    AbacEvaluateResponse,
    AbacViolationItem,
    OpaStatusResponse,
    SecurityOverviewResponse,
    SecurityScanRequest,
    SecurityScanResponse,
    VaultStatusResponse,
)
from app.services.opa_service import check_opa_health, evaluate_gateway_opa
from app.services.security_analytics_service import build_security_overview, run_security_scan
from app.services.vault_service import check_vault_status, vault_status_dict

router = APIRouter()

_require_security_read = require_permission(VIEW_AUDIT_LOGS)
_require_security_scan = require_any_permission(VIEW_AUDIT_LOGS, USE_STUDIO)
_require_abac_eval = require_any_permission(VIEW_AUDIT_LOGS, MANAGE_POLICIES, USE_STUDIO)


@router.get("/security/overview", response_model=SecurityOverviewResponse)
async def get_security_overview(
    current_user: Annotated[User, Depends(_require_security_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SecurityOverviewResponse:
    return await build_security_overview(db, current_user.tenant_id)


@router.post("/security/scan", response_model=SecurityScanResponse)
async def scan_security_content(
    payload: SecurityScanRequest,
    current_user: Annotated[User, Depends(_require_security_scan)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SecurityScanResponse:
    from app.services.security_analytics_service import dispatch_scanner_incident

    result = run_security_scan(payload)
    try:
        await dispatch_scanner_incident(
            db,
            current_user.tenant_id,
            current_user.email,
            payload.content,
            result,
        )
    except Exception:
        pass
    return result


@router.get("/security/opa/status", response_model=OpaStatusResponse)
async def get_opa_status(
    _current_user: Annotated[User, Depends(_require_security_read)],
) -> OpaStatusResponse:
    available, error = await check_opa_health()
    return OpaStatusResponse(
        enabled=settings.opa_enabled,
        available=available and settings.opa_enabled,
        policy_path=settings.opa_policy_path,
        fail_open=settings.opa_fail_open,
        base_url=settings.opa_base_url,
        error=error,
    )


@router.get("/security/vault/status", response_model=VaultStatusResponse)
async def get_vault_status(
    _current_user: Annotated[User, Depends(_require_security_read)],
) -> VaultStatusResponse:
    result = await check_vault_status(jwt_from_vault=jwt_loaded_from_vault())
    return VaultStatusResponse(**vault_status_dict(result))


@router.post("/security/opa/evaluate", response_model=AbacEvaluateResponse)
async def evaluate_abac_policy(
    payload: AbacEvaluateRequest,
    current_user: Annotated[User, Depends(_require_abac_eval)],
) -> AbacEvaluateResponse:
    del current_user
    from datetime import datetime

    input_payload = {
        "subject": {
            "role": payload.role.strip().lower(),
            "actor": payload.actor,
            "auth_type": payload.auth_type.strip().lower(),
        },
        "resource": {
            "bundle": payload.bundle,
            "tenant_id": "dry-run",
        },
        "request": {
            "model": payload.model,
            "routed_model": payload.routed_model,
        },
        "content": {
            "text_length": 0,
            "has_pii": payload.has_pii,
            "risk": payload.risk.strip().lower(),
        },
        "environment": {
            "region": payload.region.upper(),
            "hour_utc": payload.hour_utc if payload.hour_utc is not None else datetime.now(UTC).hour,
        },
        "routing_context": {},
    }
    decision = await evaluate_gateway_opa(input_payload)
    return AbacEvaluateResponse(
        allow=decision.allow,
        available=decision.available,
        skipped=decision.skipped,
        violations=[
            AbacViolationItem(rule=item.rule, message=item.message, severity=item.severity)
            for item in decision.violations
        ],
        error=decision.error,
    )
