from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.rbac import VIEW_AUDIT_LOGS, VIEW_COMPLIANCE, require_any_permission
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.data_protection import DataProtectionOverviewResponse, DlpScanRequest, DlpScanResponse
from app.services.data_protection_service import build_data_protection_overview
from app.services.dlp_service import scan_content

router = APIRouter()

_require_data_protection = require_any_permission(VIEW_COMPLIANCE, VIEW_AUDIT_LOGS)


@router.get("/data-protection/overview", response_model=DataProtectionOverviewResponse)
async def get_data_protection_overview(
    current_user: Annotated[User, Depends(_require_data_protection)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataProtectionOverviewResponse:
    return await build_data_protection_overview(db, current_user.tenant_id)


@router.post("/data-protection/scan", response_model=DlpScanResponse)
async def scan_data_protection_content(
    payload: DlpScanRequest,
    _current_user: Annotated[User, Depends(_require_data_protection)],
) -> DlpScanResponse:
    result = scan_content(payload.content)
    return DlpScanResponse(
        classifications=result.classifications,
        sensitivity_labels=result.sensitivity_labels,
        highest_sensitivity=result.highest_sensitivity,
        has_pii=result.has_pii,
        region=result.region,
        match_count=result.match_count,
        redacted_content=result.redacted_content,
    )


class CustomRuleRequest(BaseModel):
    name: str
    regex_pattern: str


@router.post("/data-protection/custom-rules", status_code=status.HTTP_201_CREATED)
async def create_custom_dlp_rule(
    payload: CustomRuleRequest,
    _current_user: Annotated[User, Depends(_require_data_protection)],
) -> dict[str, str]:
    """
    Creates a custom DLP classification rule.
    In the Community Edition, this is limited to 3 custom rules to protect the Open Core model.
    """
    # MOCK LICENSE CHECK: In reality, we would check the active license tier from the DB or license key.
    # We will simulate a tenant that already has 3 custom rules configured.
    existing_custom_rules_count = 3
    active_license_tier = "community" # Simulate the open source edition

    if active_license_tier == "community" and existing_custom_rules_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Community Edition is limited to 3 custom DLP rules. Please upgrade to PySetu AI Enterprise to unlock unlimited custom policies.",
        )
    
    return {"status": "success", "message": f"Rule {payload.name} created."}
