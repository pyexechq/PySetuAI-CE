from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.notifications import NotificationListResponse
from app.services.notification_service import list_notifications

router = APIRouter()


class NotificationReadRequest(BaseModel):
    ids: list[str]


@router.get("/notifications", response_model=NotificationListResponse)
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    read: str | None = Query(None, description="Comma-separated notification ids already read by the client"),
    limit: int = Query(30, ge=1, le=100),
) -> NotificationListResponse:
    read_ids = {item.strip() for item in read.split(",") if item.strip()} if read else set()
    return await list_notifications(db, current_user.tenant_id, read_ids, limit)
