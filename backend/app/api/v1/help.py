from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.help_chat import HelpChatRequest, HelpChatResponse
from app.services.help_assist_service import build_help_chat_response

router = APIRouter(prefix="/help", tags=["help"])


@router.post("/chat", response_model=HelpChatResponse)
async def help_chat(
    payload: HelpChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HelpChatResponse:
    return await build_help_chat_response(db, current_user.tenant_id, payload)
