from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import VIEW_AUDIT_LOGS, VIEW_COMPLIANCE, require_any_permission
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.data_protection import DataProtectionOverviewResponse
from app.services.data_protection_service import build_data_protection_overview

router = APIRouter()

_require_data_protection = require_any_permission(VIEW_COMPLIANCE, VIEW_AUDIT_LOGS)


@router.get("/data-protection/overview", response_model=DataProtectionOverviewResponse)
async def get_data_protection_overview(
    current_user: Annotated[User, Depends(_require_data_protection)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataProtectionOverviewResponse:
    return await build_data_protection_overview(db, current_user.tenant_id)
