import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_compatibility_center, require_uag_simulator
from app.core.rbac import MANAGE_LLM_PROVIDERS, require_any_permission, require_roles
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.openai import ChatCompletionRequest, ChatMessage
from app.schemas.uag import (
    UagModelMappingCreateRequest,
    UagModelMappingResponse,
    UagModelMappingUpdateRequest,
    UagSettingsResponse,
    UagSettingsUpdateRequest,
    UagSimulateRequest,
    UagSimulateResponse,
    UagStatsResponse,
)
from app.modules.uag.service import simulate_translation
from app.services.uag_admin_service import (
    build_stats,
    create_mapping,
    delete_mapping,
    get_mapping,
    get_uag_settings,
    list_mappings,
    mapping_to_dict,
    update_mapping,
    update_uag_settings,
)

router = APIRouter(prefix="/uag", tags=["Universal AI Gateway"])

POLICY_RETIRED_DETAIL = (
    "UAG translation policies are retired. Use LLM Router routing rules with target_provider instead."
)

_require_uag_admin = require_any_permission(MANAGE_LLM_PROVIDERS)
_require_uag_simulate = require_roles("tenant_admin", "platform_admin", "developer")


@router.get("/mappings", response_model=list[UagModelMappingResponse], dependencies=[Depends(require_compatibility_center)])
async def get_model_mappings(
    current_user: Annotated[User, Depends(_require_uag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UagModelMappingResponse]:
    rows = await list_mappings(db, current_user.tenant_id)
    return [UagModelMappingResponse(**mapping_to_dict(row)) for row in rows]


@router.post(
    "/mappings",
    response_model=UagModelMappingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_compatibility_center)],
)
async def post_model_mapping(
    body: UagModelMappingCreateRequest,
    current_user: Annotated[User, Depends(_require_uag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UagModelMappingResponse:
    row = await create_mapping(db, current_user.tenant_id, body.model_dump())
    return UagModelMappingResponse(**mapping_to_dict(row))


@router.put("/mappings/{mapping_id}", response_model=UagModelMappingResponse, dependencies=[Depends(require_compatibility_center)])
async def put_model_mapping(
    mapping_id: str,
    body: UagModelMappingUpdateRequest,
    current_user: Annotated[User, Depends(_require_uag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UagModelMappingResponse:
    try:
        mapping_uuid = uuid.UUID(mapping_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid mapping id") from exc
    row = await get_mapping(db, current_user.tenant_id, mapping_uuid)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    updated = await update_mapping(db, row, body.model_dump(exclude_unset=True))
    return UagModelMappingResponse(**mapping_to_dict(updated))


@router.delete(
    "/mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_compatibility_center)],
)
async def remove_model_mapping(
    mapping_id: str,
    current_user: Annotated[User, Depends(_require_uag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    try:
        mapping_uuid = uuid.UUID(mapping_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid mapping id") from exc
    row = await get_mapping(db, current_user.tenant_id, mapping_uuid)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    await delete_mapping(db, row)


@router.get("/policies", dependencies=[Depends(require_compatibility_center)])
async def get_translation_policies(
    current_user: Annotated[User, Depends(_require_uag_admin)],
) -> None:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=POLICY_RETIRED_DETAIL)


@router.post(
    "/policies",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_compatibility_center)],
)
async def post_translation_policy(
    current_user: Annotated[User, Depends(_require_uag_admin)],
) -> None:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=POLICY_RETIRED_DETAIL)


@router.put(
    "/policies/{policy_id}",
    dependencies=[Depends(require_compatibility_center)],
)
async def put_translation_policy(
    policy_id: str,
    current_user: Annotated[User, Depends(_require_uag_admin)],
) -> None:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=POLICY_RETIRED_DETAIL)


@router.delete(
    "/policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_compatibility_center)],
)
async def remove_translation_policy(
    policy_id: str,
    current_user: Annotated[User, Depends(_require_uag_admin)],
) -> None:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=POLICY_RETIRED_DETAIL)


@router.get("/stats", response_model=UagStatsResponse, dependencies=[Depends(require_compatibility_center)])
async def get_uag_stats(
    current_user: Annotated[User, Depends(_require_uag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UagStatsResponse:
    return UagStatsResponse(**await build_stats(db, current_user.tenant_id))


@router.get("/settings", response_model=UagSettingsResponse, dependencies=[Depends(require_compatibility_center)])
async def get_uag_settings_route(
    current_user: Annotated[User, Depends(_require_uag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UagSettingsResponse:
    return UagSettingsResponse(**await get_uag_settings(db, current_user.tenant_id))


@router.put("/settings", response_model=UagSettingsResponse, dependencies=[Depends(require_compatibility_center)])
async def put_uag_settings_route(
    body: UagSettingsUpdateRequest,
    current_user: Annotated[User, Depends(_require_uag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UagSettingsResponse:
    return UagSettingsResponse(
        **await update_uag_settings(db, current_user.tenant_id, body.model_dump(exclude_unset=True))
    )


@router.post("/simulate", response_model=UagSimulateResponse, dependencies=[Depends(require_uag_simulator)])
async def simulate_uag_translation(
    body: UagSimulateRequest,
    current_user: Annotated[User, Depends(_require_uag_simulate)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UagSimulateResponse:
    request = ChatCompletionRequest(
        model=body.model,
        messages=[ChatMessage(role=m.get("role", "user"), content=m.get("content", "")) for m in body.messages],
        routing_context=body.routing_context,
    )
    result = await simulate_translation(db, request, tenant_id=current_user.tenant_id)
    return UagSimulateResponse(**result)
