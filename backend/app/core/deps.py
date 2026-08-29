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
from app.models.governance import ClientApiKey
from app.models.tenant import Tenant, User

from app.services.tenant_features_service import is_feature_enabled

security = HTTPBearer(auto_error=False, scheme_name="HTTPBearer", description="JWT Bearer Token")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token_str = credentials.credentials.strip()
    if token_str.lower().startswith("bearer "):
        token_str = token_str[7:].strip()

    try:
        payload = decode_access_token(token_str)
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

    return user


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    if credentials is None:
        return None

    token_str = credentials.credentials.strip()
    if token_str.lower().startswith("bearer "):
        token_str = token_str[7:].strip()

    try:
        payload = decode_access_token(token_str)
        user_id = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(
            select(User)
            .options(selectinload(User.tenant))
            .where(User.id == uuid.UUID(str(user_id)))
        )
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None
        return user
    except Exception:
        return None


async def get_current_tenant(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Tenant:
    if not current_user.tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is inactive")
    return current_user.tenant


def require_tenant_feature(feature_key: str, *, label: str | None = None):
    async def _require(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not is_feature_enabled(current_user.tenant, feature_key):
            display = label or feature_key.replace("_", " ").title()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{display} is disabled for this tenant",
            )
        return current_user

    return _require


require_qa_dashboard_enabled = require_tenant_feature("qa_dashboard", label="QA Dashboard")
require_compatibility_center = require_tenant_feature("compatibility_center", label="Compatibility Center")
require_governance_sandbox = require_tenant_feature("governance_sandbox", label="Governance Sandbox")
require_reports = require_tenant_feature("reports", label="Reports")


async def require_uag_simulator(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    tenant = current_user.tenant
    if is_feature_enabled(tenant, "governance_sandbox") or is_feature_enabled(tenant, "compatibility_center"):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Governance Sandbox and Compatibility Center are disabled for this tenant",
    )


async def get_current_client(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClientApiKey:
    """Authenticate a non-interactive caller (e.g. the browser extension) via ClientApiKey."""
    from app.services.client_api_key_service import resolve_client_api_key, resolve_effective_api_origins

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    key = await resolve_client_api_key(db, credentials.credentials)
    if key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    tenant = await db.get(Tenant, key.tenant_id)
    if tenant is None or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is inactive")

    effective_origins = resolve_effective_api_origins(key, tenant)
    if effective_origins is not None:
        origin = request.headers.get("origin")
        if not origin or origin not in effective_origins:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed for this API key")

    return key
