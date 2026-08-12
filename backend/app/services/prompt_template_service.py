import re
import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.governance import PromptTemplate, PromptVersion
from app.schemas.prompt_template import PromptTemplateCreate, PromptTemplateUpdate, PromptVersionCreate


def extract_variables(text: str) -> list[str]:
    """Extract unique {{var_name}} template variable placeholders."""
    matches = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", text)
    seen = set()
    result = []
    for var in matches:
        if var not in seen:
            seen.add(var)
            result.append(var)
    return result


async def list_prompt_templates(db: AsyncSession, tenant_id: uuid.UUID) -> Sequence[PromptTemplate]:
    result = await db.execute(
        select(PromptTemplate)
        .options(selectinload(PromptTemplate.versions))
        .where(PromptTemplate.tenant_id == tenant_id)
        .order_by(PromptTemplate.created_at.desc())
    )
    return result.scalars().all()


async def get_prompt_template(db: AsyncSession, tenant_id: uuid.UUID, template_id: uuid.UUID) -> PromptTemplate | None:
    result = await db.execute(
        select(PromptTemplate)
        .options(selectinload(PromptTemplate.versions))
        .where(PromptTemplate.tenant_id == tenant_id, PromptTemplate.id == template_id)
    )
    return result.scalar_one_or_none()


async def create_prompt_template(
    db: AsyncSession, tenant_id: uuid.UUID, payload: PromptTemplateCreate, created_by: str | None = None
) -> PromptTemplate:
    template = PromptTemplate(
        tenant_id=tenant_id,
        name=payload.name,
        alias=payload.alias,
        description=payload.description,
        enforce_mode=payload.enforce_mode,
        is_active=True,
    )
    db.add(template)
    await db.flush()

    vars_extracted = extract_variables(payload.system_prompt)
    version = PromptVersion(
        template_id=template.id,
        version=1,
        system_prompt=payload.system_prompt,
        variables=vars_extracted,
        created_by=created_by,
    )
    db.add(version)
    await db.flush()

    template.current_version_id = version.id
    await db.commit()
    await db.refresh(template)

    # Load versions relationship
    res = await db.execute(
        select(PromptTemplate)
        .options(selectinload(PromptTemplate.versions))
        .where(PromptTemplate.id == template.id)
    )
    return res.scalar_one()


async def add_prompt_version(
    db: AsyncSession, tenant_id: uuid.UUID, template_id: uuid.UUID, payload: PromptVersionCreate, created_by: str | None = None
) -> PromptVersion:
    template = await get_prompt_template(db, tenant_id, template_id)
    if not template:
        raise ValueError("Prompt template not found")

    next_version = (max([v.version for v in template.versions], default=0)) + 1
    vars_extracted = extract_variables(payload.system_prompt)

    version = PromptVersion(
        template_id=template.id,
        version=next_version,
        system_prompt=payload.system_prompt,
        variables=vars_extracted,
        created_by=created_by,
    )
    db.add(version)
    await db.flush()

    template.current_version_id = version.id
    await db.commit()
    await db.refresh(version)
    return version


async def update_prompt_template(
    db: AsyncSession, tenant_id: uuid.UUID, template_id: uuid.UUID, payload: PromptTemplateUpdate
) -> PromptTemplate | None:
    template = await get_prompt_template(db, tenant_id, template_id)
    if not template:
        return None

    if payload.name is not None:
        template.name = payload.name
    if payload.alias is not None:
        template.alias = payload.alias
    if payload.description is not None:
        template.description = payload.description
    if payload.enforce_mode is not None:
        template.enforce_mode = payload.enforce_mode
    if payload.is_active is not None:
        template.is_active = payload.is_active

    await db.commit()
    await db.refresh(template)
    return template


async def delete_prompt_template(db: AsyncSession, tenant_id: uuid.UUID, template_id: uuid.UUID) -> bool:
    template = await get_prompt_template(db, tenant_id, template_id)
    if not template:
        return False

    await db.delete(template)
    await db.commit()
    return True
