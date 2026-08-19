import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.governance import PolicyBundle
from app.models.tenant import Tenant, User
from app.services.client_api_key_service import (
    KEY_SOURCE_PYSETU,
    looks_like_jwt,
    normalize_token_saving_mode,
    resolve_client_api_key,
    resolve_effective_api_origins,
)
from app.services.gateway_context import GatewayContext
from app.services.policy_bundle_service import get_tenant_default_bundle

security = HTTPBearer(auto_error=False)


def _enforce_origin_policy(request: Request, effective_origins: list[str] | None) -> None:
    if not effective_origins:
        return
    origin = request.headers.get("origin")
    if not origin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing Origin header")
    if origin not in effective_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed by policy")


async def get_gateway_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GatewayContext:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials.strip()

    record = await resolve_client_api_key(db, token)
    if record is not None:
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == record.tenant_id))
        tenant = tenant_result.scalar_one_or_none()
        _enforce_origin_policy(request, resolve_effective_api_origins(record, tenant))

        bundle_name = None
        if record.bundle_id:
            bundle_result = await db.execute(select(PolicyBundle).where(PolicyBundle.id == record.bundle_id))
            bundle = bundle_result.scalar_one_or_none()
            bundle_name = bundle.name if bundle else None
        await db.commit()
        key_source = record.key_source or KEY_SOURCE_PYSETU
        ingress_token = token if key_source == "mirrored" and record.upstream_pass_through else None
        return GatewayContext(
            tenant_id=record.tenant_id,
            actor=f"client-key:{record.name}",
            client_api_key_id=record.id,
            client_api_key_name=record.name,
            policy_bundle_id=record.bundle_id,
            policy_bundle_name=bundle_name,
            client_response_protocol=record.client_response_protocol,
            ai_rate_limit_rpm=record.ai_rate_limit_rpm,
            ai_rate_limit_rph=record.ai_rate_limit_rph,
            ai_rate_limit_rpd=record.ai_rate_limit_rpd,
            ai_token_limit_tpm=record.ai_token_limit_tpm,
            ai_token_limit_tph=record.ai_token_limit_tph,
            ai_token_limit_tpd=record.ai_token_limit_tpd,
            token_saving_enabled=record.token_saving_enabled,
            token_saving_mode=normalize_token_saving_mode(record.token_saving_mode),
            key_source=key_source,
            upstream_pass_through=bool(record.upstream_pass_through),
            ingress_bearer_token=ingress_token,
        )

    if not looks_like_jwt(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client API key")

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    result = await db.execute(select(User).options(selectinload(User.tenant)).where(User.id == uuid.UUID(str(user_id))))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    token_tenant_id = payload.get("tenant_id")
    if token_tenant_id and str(user.tenant_id) != str(token_tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")

    default_bundle = await get_tenant_default_bundle(db, user.tenant_id)
    return GatewayContext(
        tenant_id=user.tenant_id,
        actor=user.email,
        user=user,
        policy_bundle_id=default_bundle.id if default_bundle else None,
        policy_bundle_name=default_bundle.name if default_bundle else None,
    )
