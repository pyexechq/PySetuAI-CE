import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.governance import PolicyBundle
from app.models.tenant import User
from app.services.client_api_key_service import resolve_client_api_key
from app.services.gateway_context import GatewayContext
from app.services.policy_bundle_service import get_tenant_default_bundle

security = HTTPBearer(auto_error=False)


async def get_gateway_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GatewayContext:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials.strip()

    if token.startswith("hg_"):
        record = await resolve_client_api_key(db, token)
        if record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client API key")
        bundle_name = None
        if record.bundle_id:
            bundle_result = await db.execute(select(PolicyBundle).where(PolicyBundle.id == record.bundle_id))
            bundle = bundle_result.scalar_one_or_none()
            bundle_name = bundle.name if bundle else None
        await db.commit()
        return GatewayContext(
            tenant_id=record.tenant_id,
            actor=f"client-key:{record.name}",
            client_api_key_id=record.id,
            client_api_key_name=record.name,
            policy_bundle_id=record.bundle_id,
            policy_bundle_name=bundle_name,
            client_response_protocol=record.client_response_protocol,
        )

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
