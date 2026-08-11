import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rbac import (
    ALL_PERMISSIONS,
    MANAGE_USERS,
    VALID_ROLES,
    permissions_for_role,
    require_permission,
    role_has_permission,
)
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.users import (
    RbacMatrixResponse,
    RbacPermissionsResponse,
    TenantUserCreateRequest,
    TenantUserResponse,
    TenantUserUpdateRequest,
)

router = APIRouter()


def _user_response(user: User) -> TenantUserResponse:
    return TenantUserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
    )


@router.get("/users", response_model=list[TenantUserResponse])
async def list_users(
    current_user: Annotated[User, Depends(require_permission(MANAGE_USERS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TenantUserResponse]:
    result = await db.execute(select(User).where(User.tenant_id == current_user.tenant_id).order_by(User.email))
    users = list(result.scalars().all())
    return [_user_response(u) for u in users]


@router.post("/users", response_model=TenantUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: TenantUserCreateRequest,
    current_user: Annotated[User, Depends(require_permission(MANAGE_USERS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantUserResponse:
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}",
        )

    email = payload.email.strip().lower()
    existing = await db.execute(select(User).where(User.tenant_id == current_user.tenant_id, User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered for this tenant")

    user = User(
        tenant_id=current_user.tenant_id,
        email=email,
        name=payload.name.strip(),
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _user_response(user)


@router.patch("/users/{user_id}", response_model=TenantUserResponse)
async def update_user(
    user_id: str,
    payload: TenantUserUpdateRequest,
    current_user: Annotated[User, Depends(require_permission(MANAGE_USERS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantUserResponse:
    if payload.role is None and payload.is_active is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide role and/or is_active to update",
        )

    if payload.role is not None and payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}",
        )

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id") from exc

    result = await db.execute(select(User).where(User.id == user_uuid, User.tenant_id == current_user.tenant_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(user.id) == str(current_user.id) and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    return _user_response(user)


@router.get("/rbac/permissions", response_model=RbacPermissionsResponse)
async def get_rbac_permissions(
    current_user: Annotated[User, Depends(get_current_user)],
) -> RbacPermissionsResponse:
    return RbacPermissionsResponse(
        role=current_user.role,
        permissions=permissions_for_role(current_user.role),
    )


@router.get("/rbac/matrix", response_model=RbacMatrixResponse)
async def get_rbac_matrix(
    current_user: Annotated[User, Depends(get_current_user)],
) -> RbacMatrixResponse:
    matrix: dict[str, dict[str, bool]] = {}
    for role in VALID_ROLES:
        matrix[role] = {perm: role_has_permission(role, perm) for perm in ALL_PERMISSIONS}
    return RbacMatrixResponse(
        permissions=list(ALL_PERMISSIONS),
        roles=list(VALID_ROLES),
        matrix=matrix,
    )
