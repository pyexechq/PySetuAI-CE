import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import MANAGE_LLM_PROVIDERS, require_permission
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.integrations import (
    AlertWebhookCreateRequest,
    AlertWebhookResponse,
    AlertWebhookTestResponse,
    AlertWebhookUpdateRequest,
)
from app.services.alert_webhook_service import (
    create_webhook,
    delete_webhook,
    get_webhook,
    list_webhooks,
    send_test_alert,
    update_webhook,
    webhook_to_dict,
)

router = APIRouter(prefix="/settings/alert-webhooks", tags=["Integrations"])

_require_integrations_admin = require_permission(MANAGE_LLM_PROVIDERS)


@router.get("", response_model=list[AlertWebhookResponse])
async def list_alert_webhooks(
    current_user: Annotated[User, Depends(_require_integrations_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AlertWebhookResponse]:
    webhooks = await list_webhooks(db, current_user.tenant_id)
    return [AlertWebhookResponse(**webhook_to_dict(w)) for w in webhooks]


@router.post("", response_model=AlertWebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_webhook(
    body: AlertWebhookCreateRequest,
    current_user: Annotated[User, Depends(_require_integrations_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AlertWebhookResponse:
    try:
        webhook = await create_webhook(db, current_user.tenant_id, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AlertWebhookResponse(**webhook_to_dict(webhook))


@router.put("/{webhook_id}", response_model=AlertWebhookResponse)
async def update_alert_webhook(
    webhook_id: str,
    body: AlertWebhookUpdateRequest,
    current_user: Annotated[User, Depends(_require_integrations_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AlertWebhookResponse:
    try:
        webhook_uuid = uuid.UUID(webhook_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook id") from exc

    webhook = await get_webhook(db, current_user.tenant_id, webhook_uuid)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    try:
        updated = await update_webhook(db, webhook, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AlertWebhookResponse(**webhook_to_dict(updated))


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_webhook(
    webhook_id: str,
    current_user: Annotated[User, Depends(_require_integrations_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    try:
        webhook_uuid = uuid.UUID(webhook_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook id") from exc

    webhook = await get_webhook(db, current_user.tenant_id, webhook_uuid)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    await delete_webhook(db, webhook)


@router.post("/{webhook_id}/test", response_model=AlertWebhookTestResponse)
async def test_alert_webhook(
    webhook_id: str,
    current_user: Annotated[User, Depends(_require_integrations_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AlertWebhookTestResponse:
    try:
        webhook_uuid = uuid.UUID(webhook_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook id") from exc

    webhook = await get_webhook(db, current_user.tenant_id, webhook_uuid)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    try:
        result = await send_test_alert(db, webhook)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AlertWebhookTestResponse(
        webhook_id=result.webhook_id,
        webhook_name=result.webhook_name,
        message=result.message,
    )
