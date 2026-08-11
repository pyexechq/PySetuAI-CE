from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.rbac import MANAGE_LLM_PROVIDERS, require_permission, require_roles
from app.db.session import get_db
from app.models.governance import TenantIntegration
from app.models.tenant import Tenant, User
from app.schemas.settings import (
    IntegrationSettingsResponse,
    IntegrationSettingsUpdate,
    OrganizationSettingsResponse,
    OrganizationSettingsUpdate,
)
from app.services.integration_service import get_or_create_integration, mask_secret, resolve_gateway_config
from app.services.secrets_service import (
    GEMINI_SECRET,
    OPENAI_SECRET,
    get_tenant_secret,
    secrets_backend_name,
    set_tenant_secret,
    vault_auth_method_name,
)
from app.services.tenant_branding_service import branding_dict, update_tenant_branding

router = APIRouter()

_require_llm_admin = require_permission(MANAGE_LLM_PROVIDERS)
_require_org_admin = require_roles("tenant_admin", "platform_admin")


async def _integration_response(
    db: AsyncSession,
    tenant_id,
    row: TenantIntegration | None,
    config,
) -> IntegrationSettingsResponse:
    openai_secret = await get_tenant_secret(db, tenant_id, OPENAI_SECRET)
    gemini_secret = await get_tenant_secret(db, tenant_id, GEMINI_SECRET)
    if openai_secret is None and row is None:
        openai_secret = settings.openai_api_key
    if gemini_secret is None and row is None:
        gemini_secret = settings.gemini_api_key

    return IntegrationSettingsResponse(
        openai_api_key_set=bool(openai_secret),
        openai_api_key_masked=mask_secret(openai_secret),
        gemini_api_key_set=bool(gemini_secret),
        gemini_api_key_masked=mask_secret(gemini_secret),
        gemini_default_model=row.gemini_default_model if row else settings.gemini_default_model,
        ollama_enabled=row.ollama_enabled if row else settings.ollama_enabled,
        ollama_base_url=row.ollama_base_url if row else settings.ollama_base_url,
        ollama_default_model=row.ollama_default_model if row else settings.ollama_default_model,
        active_upstream=config.upstream,
        config_source=config.source,
        secrets_backend=secrets_backend_name(),
        vault_auth_method=vault_auth_method_name(),
    )


@router.get("/settings/integrations", response_model=IntegrationSettingsResponse)
async def get_integrations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IntegrationSettingsResponse:
    result = await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == current_user.tenant_id))
    row = result.scalar_one_or_none()
    config = await resolve_gateway_config(db, current_user.tenant_id)
    return await _integration_response(db, current_user.tenant_id, row, config)


@router.put("/settings/integrations", response_model=IntegrationSettingsResponse)
async def update_integrations(
    payload: IntegrationSettingsUpdate,
    current_user: Annotated[User, Depends(_require_llm_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IntegrationSettingsResponse:
    row = await get_or_create_integration(db, current_user.tenant_id)

    if payload.openai_api_key is not None:
        await set_tenant_secret(
            db,
            current_user.tenant_id,
            OPENAI_SECRET,
            payload.openai_api_key.strip() or None,
        )
    if payload.gemini_api_key is not None:
        await set_tenant_secret(
            db,
            current_user.tenant_id,
            GEMINI_SECRET,
            payload.gemini_api_key.strip() or None,
        )
    if payload.gemini_default_model is not None:
        row.gemini_default_model = payload.gemini_default_model.strip() or row.gemini_default_model
    if payload.ollama_enabled is not None:
        row.ollama_enabled = payload.ollama_enabled
    if payload.ollama_base_url is not None:
        row.ollama_base_url = payload.ollama_base_url.strip() or row.ollama_base_url
    if payload.ollama_default_model is not None:
        row.ollama_default_model = payload.ollama_default_model.strip() or row.ollama_default_model

    await db.commit()
    await db.refresh(row)
    config = await resolve_gateway_config(db, current_user.tenant_id)
    return await _integration_response(db, current_user.tenant_id, row, config)


@router.get("/settings/organization", response_model=OrganizationSettingsResponse)
async def get_organization_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSettingsResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one()
    return OrganizationSettingsResponse(**branding_dict(tenant))


@router.put("/settings/organization", response_model=OrganizationSettingsResponse)
async def update_organization_settings(
    payload: OrganizationSettingsUpdate,
    current_user: Annotated[User, Depends(_require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSettingsResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one()
    updated = await update_tenant_branding(db, tenant, payload.model_dump(exclude_unset=True))
    return OrganizationSettingsResponse(**branding_dict(updated))
