"""Policy bundles and client API key management."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import MANAGE_POLICIES, USE_MCP, USE_STUDIO, require_any_permission, require_permission
from app.db.session import get_db
from app.models.governance import ClientApiKey, Policy, PolicyBundle
from app.models.tenant import User
from app.schemas.access import (
    ClientApiKeyCreateRequest,
    ClientApiKeyCreateResponse,
    ClientApiKeyMirroredCreateRequest,
    ClientApiKeyRevealResponse,
    ClientApiKeyResponse,
    ClientApiKeyUpdateRequest,
    FrameworkRulePackResponse,
    McpScopeConfig,
    PolicyBundleCreateRequest,
    PolicyBundleResponse,
    PolicyBundleUpdateRequest,
)
from app.config import settings
from app.services.client_api_key_service import (
    client_key_response,
    decrypt_client_key,
    encrypt_client_key,
    generate_client_key,
    get_client_api_key,
    normalize_api_key_client_protocol,
    normalize_token_saving_mode,
    register_mirrored_client_key,
    validate_api_origins,
    validate_bundle_for_tenant,
)
from app.services.framework_rule_packs import list_framework_rule_packs
from app.services.policy_bundle_service import clear_other_defaults, get_policy_bundle

router = APIRouter()

_require_policy_admin = require_permission(MANAGE_POLICIES)
_require_key_management = require_any_permission(MANAGE_POLICIES, USE_MCP, USE_STUDIO)


def _parse_allowed_api_origins(origins: list[str] | None) -> list[str] | None:
    try:
        return validate_api_origins(origins)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _bundle_response(bundle: PolicyBundle, policy_names: dict[str, str] | None = None) -> PolicyBundleResponse:
    ids = bundle.policy_ids if isinstance(bundle.policy_ids, list) else []
    names = [policy_names.get(str(i), str(i)) for i in ids] if policy_names else []
    c_ids = bundle.custom_intent_ids if isinstance(bundle.custom_intent_ids, list) else []
    mcp_scope = None
    if bundle.mcp_scope and isinstance(bundle.mcp_scope, dict):
        mcp_scope = McpScopeConfig.model_validate(bundle.mcp_scope)
    packs = bundle.framework_rule_packs if isinstance(bundle.framework_rule_packs, list) else []
    return PolicyBundleResponse(
        id=str(bundle.id),
        name=bundle.name,
        description=bundle.description or "",
        status=bundle.status,
        is_default=bundle.is_default,
        policy_ids=[str(i) for i in ids],
        custom_intent_ids=[str(i) for i in c_ids],
        policy_names=names,
        framework_rule_packs=[str(p) for p in packs],
        mcp_scope=mcp_scope,
        target_domains=list(bundle.target_domains) if isinstance(bundle.target_domains, list) else [],
        created_at=bundle.created_at.isoformat() if bundle.created_at else "",
    )


async def _validate_mcp_scope(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    scope: McpScopeConfig | None,
) -> dict | None:
    if scope is None:
        return None
    mode = (scope.mode or "all").strip().lower()
    if mode not in {"all", "allowlist"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid mcp_scope.mode")
    if mode == "all":
        return {"mode": "all", "entries": []}
    server_ids: list[uuid.UUID] = []
    for entry in scope.entries:
        try:
            server_ids.append(uuid.UUID(str(entry.server_id)))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MCP server id: {entry.server_id}",
            ) from exc
    if not server_ids:
        return {"mode": "allowlist", "entries": []}
    from app.models.governance import MCPServer

    result = await db.execute(
        select(MCPServer.id).where(MCPServer.tenant_id == tenant_id, MCPServer.id.in_(server_ids))
    )
    found = {str(row[0]) for row in result.all()}
    entries: list[dict] = []
    for entry in scope.entries:
        if str(entry.server_id) not in found:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MCP server not found: {entry.server_id}",
            )
        entries.append(
            {
                "server_id": str(entry.server_id),
                "tool_names": [str(t) for t in entry.tool_names],
            }
        )
    return {"mode": "allowlist", "entries": entries}


def _validate_framework_packs(pack_ids: list[str]) -> list[str]:
    """Validate framework rule pack ids against the catalog."""
    from app.services.framework_rule_packs import get_framework_rule_pack

    if not pack_ids:
        return []
    seen: list[str] = []
    for raw in pack_ids:
        pack_id = str(raw).strip()
        if not pack_id:
            continue
        if get_framework_rule_pack(pack_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown framework rule pack: {pack_id}")
        if pack_id not in seen:
            seen.append(pack_id)
    return seen


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


async def _validate_custom_intent_ids(db: AsyncSession, tenant_id: uuid.UUID, custom_intent_ids: list[str]) -> list[str]:
    if not custom_intent_ids:
        return []
    from app.models.governance import CustomIntent
    uuids: list[uuid.UUID] = []
    for raw in custom_intent_ids:
        try:
            uuids.append(uuid.UUID(str(raw)))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid custom intent id: {raw}") from exc
    result = await db.execute(
        select(CustomIntent.id).where(
            CustomIntent.tenant_id == tenant_id,
            CustomIntent.id.in_(uuids),
        )
    )
    found = {str(row[0]) for row in result.all()}
    ordered = [str(raw) for raw in custom_intent_ids if str(raw) in found]
    if len(ordered) != len(custom_intent_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more custom intent ids were not found")
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


@router.get("/policy-bundles/framework-packs", response_model=list[FrameworkRulePackResponse])
async def list_framework_packs(
    _current_user: Annotated[User, Depends(_require_policy_admin)],
) -> list[FrameworkRulePackResponse]:
    """List the available config-driven framework rule packs."""
    return [FrameworkRulePackResponse(**pack) for pack in list_framework_rule_packs()]


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
    custom_intent_ids = await _validate_custom_intent_ids(db, current_user.tenant_id, payload.custom_intent_ids)
    if payload.is_default:
        await clear_other_defaults(db, current_user.tenant_id)
    bundle = PolicyBundle(
        tenant_id=current_user.tenant_id,
        name=name,
        description=(payload.description or "").strip(),
        status=payload.status,
        is_default=payload.is_default,
        policy_ids=policy_ids,
        custom_intent_ids=custom_intent_ids,
        mcp_scope=await _validate_mcp_scope(db, current_user.tenant_id, payload.mcp_scope),
        target_domains=payload.target_domains,
        framework_rule_packs=_validate_framework_packs(payload.framework_rule_packs),
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
    if payload.custom_intent_ids is not None:
        bundle.custom_intent_ids = await _validate_custom_intent_ids(db, current_user.tenant_id, payload.custom_intent_ids)
    if payload.mcp_scope is not None:
        bundle.mcp_scope = await _validate_mcp_scope(db, current_user.tenant_id, payload.mcp_scope)
    if payload.target_domains is not None:
        bundle.target_domains = [domain.strip().lower() for domain in payload.target_domains if domain.strip()]
    if payload.framework_rule_packs is not None:
        bundle.framework_rule_packs = _validate_framework_packs(payload.framework_rule_packs)
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
    current_user: Annotated[User, Depends(_require_key_management)],
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
    current_user: Annotated[User, Depends(_require_key_management)],
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
        key_encrypted=encrypt_client_key(full_key),
        bundle_id=bundle_uuid,
        client_response_protocol=normalize_api_key_client_protocol(payload.client_response_protocol),
        ai_rate_limit_rpm=payload.ai_rate_limit_rpm,
        ai_rate_limit_rph=payload.ai_rate_limit_rph,
        ai_rate_limit_rpd=payload.ai_rate_limit_rpd,
        ai_token_limit_tpm=payload.ai_token_limit_tpm,
        ai_token_limit_tph=payload.ai_token_limit_tph,
        ai_token_limit_tpd=payload.ai_token_limit_tpd,
        token_saving_enabled=payload.token_saving_enabled,
        token_saving_mode=normalize_token_saving_mode(payload.token_saving_mode),
        allowed_api_origins=_parse_allowed_api_origins(payload.allowed_api_origins),
        key_source="pysetu",
        upstream_pass_through=False,
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


@router.get("/client-api-keys/{key_id}/reveal", response_model=ClientApiKeyRevealResponse)
async def reveal_client_api_key(
    key_id: str,
    current_user: Annotated[User, Depends(_require_key_management)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClientApiKeyRevealResponse:
    record = await get_client_api_key(db, current_user.tenant_id, key_id)
    if not record.key_encrypted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This key was created before reveal support and cannot be recovered",
        )
    try:
        api_key = decrypt_client_key(record.key_encrypted)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return ClientApiKeyRevealResponse(id=str(record.id), name=record.name, api_key=api_key)


@router.post("/client-api-keys/mirrored", response_model=ClientApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_mirrored_client_api_key(
    payload: ClientApiKeyMirroredCreateRequest,
    current_user: Annotated[User, Depends(_require_policy_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClientApiKeyResponse:
    if not settings.byok_ingress_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="BYOK ingress is disabled on this deployment")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Key name is required")

    mirrored_key = payload.mirrored_api_key.strip()
    if not mirrored_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mirrored API key is required")

    bundle_uuid = await validate_bundle_for_tenant(db, current_user.tenant_id, payload.bundle_id)
    record = await register_mirrored_client_key(
        db,
        current_user.tenant_id,
        name=name,
        raw_key=mirrored_key,
        description=(payload.description or "").strip(),
        bundle_id=bundle_uuid,
        client_response_protocol=normalize_api_key_client_protocol(payload.client_response_protocol),
        upstream_pass_through=payload.upstream_pass_through,
        allowed_api_origins=_parse_allowed_api_origins(payload.allowed_api_origins),
        ai_rate_limit_rpm=payload.ai_rate_limit_rpm,
        ai_rate_limit_rph=payload.ai_rate_limit_rph,
        ai_rate_limit_rpd=payload.ai_rate_limit_rpd,
        ai_token_limit_tpm=payload.ai_token_limit_tpm,
        ai_token_limit_tph=payload.ai_token_limit_tph,
        ai_token_limit_tpd=payload.ai_token_limit_tpd,
        token_saving_enabled=payload.token_saving_enabled,
        token_saving_mode=normalize_token_saving_mode(payload.token_saving_mode),
    )
    await db.commit()
    await db.refresh(record)
    bundle_name = None
    if record.bundle_id:
        bundle = await get_policy_bundle(db, current_user.tenant_id, str(record.bundle_id))
        bundle_name = bundle.name
    return ClientApiKeyResponse(**client_key_response(record, bundle_name=bundle_name))


@router.put("/client-api-keys/{key_id}", response_model=ClientApiKeyResponse)
async def update_client_api_key(
    key_id: str,
    payload: ClientApiKeyUpdateRequest,
    current_user: Annotated[User, Depends(_require_key_management)],
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
    
    if payload.ai_rate_limit_rpm is not None:
        record.ai_rate_limit_rpm = payload.ai_rate_limit_rpm
    if payload.ai_rate_limit_rph is not None:
        record.ai_rate_limit_rph = payload.ai_rate_limit_rph
    if payload.ai_rate_limit_rpd is not None:
        record.ai_rate_limit_rpd = payload.ai_rate_limit_rpd
    if payload.ai_token_limit_tpm is not None:
        record.ai_token_limit_tpm = payload.ai_token_limit_tpm
    if payload.ai_token_limit_tph is not None:
        record.ai_token_limit_tph = payload.ai_token_limit_tph
    if payload.ai_token_limit_tpd is not None:
        record.ai_token_limit_tpd = payload.ai_token_limit_tpd
    if payload.token_saving_enabled is not None:
        record.token_saving_enabled = payload.token_saving_enabled
    if payload.token_saving_mode is not None:
        record.token_saving_mode = normalize_token_saving_mode(payload.token_saving_mode)
    if payload.allowed_api_origins is not None:
        record.allowed_api_origins = _parse_allowed_api_origins(payload.allowed_api_origins)
    if payload.upstream_pass_through is not None:
        if record.key_source != "mirrored":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upstream pass-through applies only to mirrored keys",
            )
        record.upstream_pass_through = payload.upstream_pass_through

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
    current_user: Annotated[User, Depends(_require_key_management)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    record = await get_client_api_key(db, current_user.tenant_id, key_id)
    await db.delete(record)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
