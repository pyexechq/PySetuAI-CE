from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.governance import RoutingGroup
from app.models.tenant import User
from app.schemas.routing_groups import (
    RoutingGroupCreate,
    RoutingGroupResponse,
    RoutingGroupUpdate,
)

router = APIRouter(prefix="/routing-groups", tags=["LLM Routing Groups"])


@router.get("", response_model=list[RoutingGroupResponse])
async def list_routing_groups(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RoutingGroupResponse]:
    result = await db.execute(
        select(RoutingGroup)
        .where(RoutingGroup.tenant_id == current_user.tenant_id)
        .order_by(RoutingGroup.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=RoutingGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_routing_group(
    body: RoutingGroupCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoutingGroupResponse:
    group = RoutingGroup(
        tenant_id=current_user.tenant_id,
        name=body.name,
        description=body.description,
        strategy=body.strategy,
        members=[m.model_dump() for m in body.members],
        status=body.status,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


@router.get("/{group_id}", response_model=RoutingGroupResponse)
async def get_routing_group(
    group_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoutingGroupResponse:
    result = await db.execute(
        select(RoutingGroup).where(
            RoutingGroup.id == group_id,
            RoutingGroup.tenant_id == current_user.tenant_id,
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing group not found")
    return group


@router.put("/{group_id}", response_model=RoutingGroupResponse)
async def update_routing_group(
    group_id: UUID,
    body: RoutingGroupUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RoutingGroupResponse:
    result = await db.execute(
        select(RoutingGroup).where(
            RoutingGroup.id == group_id,
            RoutingGroup.tenant_id == current_user.tenant_id,
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing group not found")

    if body.name is not None:
        group.name = body.name
    if body.description is not None:
        group.description = body.description
    if body.strategy is not None:
        group.strategy = body.strategy
    if body.members is not None:
        group.members = [m.model_dump() for m in body.members]
    if body.status is not None:
        group.status = body.status

    await db.commit()
    await db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_group(
    group_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(
        select(RoutingGroup).where(
            RoutingGroup.id == group_id,
            RoutingGroup.tenant_id == current_user.tenant_id,
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing group not found")

    await db.delete(group)
    await db.commit()
