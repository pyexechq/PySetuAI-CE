import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.prompt_template import (
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTemplateUpdate,
    PromptVersionCreate,
    PromptVersionResponse,
)
from app.services import prompt_template_service

router = APIRouter(prefix="/prompt-templates", tags=["Prompt Templates"])


@router.get("", response_model=list[PromptTemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    templates = await prompt_template_service.list_prompt_templates(db, user.tenant_id)
    out = []
    for t in templates:
        curr_ver = None
        if t.versions:
            ver_obj = next((v for v in t.versions if v.id == t.current_version_id), t.versions[-1])
            curr_ver = PromptVersionResponse.model_validate(ver_obj)
        resp = PromptTemplateResponse.model_validate(t)
        resp.current_version = curr_ver
        out.append(resp)
    return out


@router.post("", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    template = await prompt_template_service.create_prompt_template(db, user.tenant_id, payload, created_by=user.email)
    curr_ver = None
    if template.versions:
        ver_obj = next((v for v in template.versions if v.id == template.current_version_id), template.versions[-1])
        curr_ver = PromptVersionResponse.model_validate(ver_obj)
    resp = PromptTemplateResponse.model_validate(template)
    resp.current_version = curr_ver
    return resp


@router.get("/{template_id}", response_model=PromptTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    template = await prompt_template_service.get_prompt_template(db, user.tenant_id, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found")

    curr_ver = None
    if template.versions:
        ver_obj = next((v for v in template.versions if v.id == template.current_version_id), template.versions[-1])
        curr_ver = PromptVersionResponse.model_validate(ver_obj)
    resp = PromptTemplateResponse.model_validate(template)
    resp.current_version = curr_ver
    return resp


@router.put("/{template_id}", response_model=PromptTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    payload: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    template = await prompt_template_service.update_prompt_template(db, user.tenant_id, template_id, payload)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found")

    curr_ver = None
    if template.versions:
        ver_obj = next((v for v in template.versions if v.id == template.current_version_id), template.versions[-1])
        curr_ver = PromptVersionResponse.model_validate(ver_obj)
    resp = PromptTemplateResponse.model_validate(template)
    resp.current_version = curr_ver
    return resp


@router.post("/{template_id}/versions", response_model=PromptVersionResponse, status_code=status.HTTP_201_CREATED)
async def add_version(
    template_id: uuid.UUID,
    payload: PromptVersionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    try:
        version = await prompt_template_service.add_prompt_version(db, user.tenant_id, template_id, payload, created_by=user.email)
        return version
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    deleted = await prompt_template_service.delete_prompt_template(db, user.tenant_id, template_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found")
