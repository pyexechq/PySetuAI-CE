"""Policy bundles and client API key management."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import MANAGE_POLICIES, require_permission
from app.db.session import get_db
from app.models.governance import ClientApiKey, Policy, PolicyBundle
from app.models.tenant import User
from app.schemas.access import (
    ClientApiKeyCreateRequest,
    ClientApiKeyCreateResponse,
    ClientApiKeyResponse,
    ClientApiKeyUpdateRequest,
    PolicyBundleCreateRequest,
    PolicyBundleResponse,
    PolicyBundleUpdateRequest,
)
from app.services.client_api_key_service import (
    client_key_response,
    generate_client_key,
    get_client_api_key,
    normalize_api_key_client_protocol,
    validate_bundle_for_tenant,
)
from app.services.policy_bundle_service import clear_other_defaults, get_policy_bundle

router = APIRouter()

_require_policy_admin = require_permission(MANAGE_POLICIES)


def _bundle_response(bundle: PolicyBundle, policy_names: dict[str, str] | None = None) -> PolicyBundleResponse:
    ids = bundle.policy_ids if isinstance(bundle.policy_ids, list) else []
    names = [policy_names.get(str(i), str(i)) for i in ids] if policy_names else []
    return PolicyBundleResponse(
        id=str(bundle.id),
        name=bundle.name,
        description=bundle.description or "",
        status=bundle.status,
        is_default=bundle.is_default,
        policy_ids=[str(i) for i in ids],
        policy_names=names,
        created_at=bundle.created_at.isoformat() if bundle.created_at else "",
    )


async def _policy_name_map(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, str]:
    result = await db.execute(select(Policy).where(Policy.tenant_id == tenant_id, Policy.policy_type == "policy"))
    return {str(p.id): p.name for p in result.scalars().all()}


async def _validate_policy_ids(db: AsyncSession, tenant_id: uuid.UUID, policy_ids: list[str]) -> list[str]:
    if not policy_ids:
        return []
    uuids: list[uuid.UUID] = []
    for raw in policy_ids:
        try:
            uuids.append(uuid.UUID(str(raw)))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid policy id: {raw}") from exc
    result = await db.execute(
        select(Policy.id).where(
            Policy.tenant_id == tenant_id,
            Policy.id.in_(uuids),
            Policy.policy_type == "policy",
        )
    )
    found = {str(row[0]) for row in result.all()}
    ordered = [str(raw) for raw in policy_ids if str(raw) in found]
    if len(ordered) != len(policy_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more policy ids were not found")
    return ordered


@router.get("/policy-bundles", response_model=list[PolicyBundleResponse])
async def list_policy_bundles(
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PolicyBundleResponse]:
    result = await db.execute(
        select(PolicyBundle).where(PolicyBundle.tenant_id == current_user.tenant_id).order_by(PolicyBundle.name.asc())
    )
    bundles = list(result.scalars().all())
    names = await _policy_name_map(db, current_user.tenant_id)
    return [_bundle_response(b, names) for b in bundles]


@router.post("/policy-bundles", response_model=PolicyBundleResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_bundle(
    payload: PolicyBundleCreateRequest,
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyBundleResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bundle name is required")
    policy_ids = await _validate_policy_ids(db, current_user.tenant_id, payload.policy_ids)
    if payload.is_default:
        await clear_other_defaults(db, current_user.tenant_id)
    bundle = PolicyBundle(
        tenant_id=current_user.tenant_id,
        name=name,
        description=(payload.description or "").strip(),
        status=payload.status,
        is_default=payload.is_default,
        policy_ids=policy_ids,
    )
    db.add(bundle)
    await db.commit()
    await db.refresh(bundle)
    names = await _policy_name_map(db, current_user.tenant_id)
    return _bundle_response(bundle, names)


@router.put("/policy-bundles/{bundle_id}", response_model=PolicyBundleResponse)
async def update_policy_bundle(
    bundle_id: str,
    payload: PolicyBundleUpdateRequest,
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyBundleResponse:
    bundle = await get_policy_bundle(db, current_user.tenant_id, bundle_id)
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bundle name is required")
        bundle.name = name
    if payload.description is not None:
        bundle.description = payload.description.strip()
    if payload.status is not None:
        if payload.status not in {"active", "draft", "disabled"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bundle status")
        bundle.status = payload.status
    if payload.policy_ids is not None:
        bundle.policy_ids = await _validate_policy_ids(db, current_user.tenant_id, payload.policy_ids)
    if payload.is_default is not None:
        if payload.is_default:
            await clear_other_defaults(db, current_user.tenant_id, except_id=bundle.id)
        bundle.is_default = payload.is_default
    await db.commit()
    await db.refresh(bundle)
    names = await _policy_name_map(db, current_user.tenant_id)
    return _bundle_response(bundle, names)


@router.delete("/policy-bundles/{bundle_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_policy_bundle(
    bundle_id: str,
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    bundle = await get_policy_bundle(db, current_user.tenant_id, bundle_id)
    await db.delete(bundle)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/client-api-keys", response_model=list[ClientApiKeyResponse])
async def list_client_api_keys(
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ClientApiKeyResponse]:
    result = await db.execute(
        select(ClientApiKey).where(ClientApiKey.tenant_id == current_user.tenant_id).order_by(ClientApiKey.name.asc())
    )
    keys = list(result.scalars().all())
    bundle_names: dict[str, str] = {}
    if keys:
        bundle_ids = [k.bundle_id for k in keys if k.bundle_id]
        if bundle_ids:
            bundles = await db.execute(select(PolicyBundle).where(PolicyBundle.id.in_(bundle_ids)))
            bundle_names = {str(b.id): b.name for b in bundles.scalars().all()}
    return [
        ClientApiKeyResponse(
            **client_key_response(k, bundle_name=bundle_names.get(str(k.bundle_id)) if k.bundle_id else None)
        )
        for k in keys
    ]


@router.post("/client-api-keys", response_model=ClientApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_client_api_key(
    payload: ClientApiKeyCreateRequest,
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClientApiKeyCreateResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Key name is required")
    bundle_uuid = await validate_bundle_for_tenant(db, current_user.tenant_id, payload.bundle_id)
    full_key, key_prefix, key_hash = generate_client_key()
    record = ClientApiKey(
        tenant_id=current_user.tenant_id,
        name=name,
        description=(payload.description or "").strip(),
        key_prefix=key_prefix,
        key_hash=key_hash,
        bundle_id=bundle_uuid,
        client_response_protocol=normalize_api_key_client_protocol(payload.client_response_protocol),
        is_active=True,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    bundle_name = None
    if record.bundle_id:
        bundle = await get_policy_bundle(db, current_user.tenant_id, str(record.bundle_id))
        bundle_name = bundle.name
    base = client_key_response(record, bundle_name=bundle_name)
    return ClientApiKeyCreateResponse(**base, api_key=full_key)


@router.put("/client-api-keys/{key_id}", response_model=ClientApiKeyResponse)
async def update_client_api_key(
    key_id: str,
    payload: ClientApiKeyUpdateRequest,
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClientApiKeyResponse:
    record = await get_client_api_key(db, current_user.tenant_id, key_id)
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Key name is required")
        record.name = name
    if payload.description is not None:
        record.description = payload.description.strip()
    if payload.bundle_id is not None:
        record.bundle_id = await validate_bundle_for_tenant(db, current_user.tenant_id, payload.bundle_id or None)
    if payload.client_response_protocol is not None:
        record.client_response_protocol = normalize_api_key_client_protocol(payload.client_response_protocol)
    if payload.is_active is not None:
        record.is_active = payload.is_active
    await db.commit()
    await db.refresh(record)
    bundle_name = None
    if record.bundle_id:
        bundle = await get_policy_bundle(db, current_user.tenant_id, str(record.bundle_id))
        bundle_name = bundle.name
    return ClientApiKeyResponse(**client_key_response(record, bundle_name=bundle_name))


@router.delete("/client-api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_client_api_key(
    key_id: str,
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    record = await get_client_api_key(db, current_user.tenant_id, key_id)
    await db.delete(record)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
