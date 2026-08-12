import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.custom_intent import (
    CustomIntentCreate,
    CustomIntentResponse,
    CustomIntentTestRequest,
    CustomIntentTestResponse,
    CustomIntentUpdate,
    CustomIntentAssistRequest,
    CustomIntentAssistResponse,
)
from app.services.custom_intent_service import CustomIntentService

router = APIRouter(prefix="/governance/custom-intents", tags=["Custom Intents"])


@router.get("", response_model=List[CustomIntentResponse])
async def list_custom_intents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CustomIntentService.list_custom_intents(db, current_user.tenant_id)


@router.post("", response_model=CustomIntentResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_intent(
    data: CustomIntentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CustomIntentService.create_custom_intent(db, current_user.tenant_id, data)


@router.get("/{intent_id}", response_model=CustomIntentResponse)
async def get_custom_intent(
    intent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    intent = await CustomIntentService.get_custom_intent(db, current_user.tenant_id, intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="Custom intent not found")
    return intent


@router.put("/{intent_id}", response_model=CustomIntentResponse)
async def update_custom_intent(
    intent_id: uuid.UUID,
    data: CustomIntentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    intent = await CustomIntentService.update_custom_intent(db, current_user.tenant_id, intent_id, data)
    if not intent:
        raise HTTPException(status_code=404, detail="Custom intent not found")
    return intent


@router.delete("/{intent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_intent(
    intent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await CustomIntentService.delete_custom_intent(db, current_user.tenant_id, intent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Custom intent not found")


@router.post("/test", response_model=CustomIntentTestResponse)
async def test_custom_intent(
    data: CustomIntentTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CustomIntentService.scan_prompt_intents(
        db, current_user.tenant_id, data.prompt, data.intent_ids
    )


@router.post("/assist", response_model=CustomIntentAssistResponse)
async def assist_custom_intent(
    data: CustomIntentAssistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await CustomIntentService.suggest_custom_intent_with_ai(
        db, current_user.tenant_id, data.goal
    )
    return result

