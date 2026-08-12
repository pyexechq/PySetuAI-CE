from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.rbac import MANAGE_LLM_PROVIDERS, require_permission, require_roles
from app.db.session import get_db
from app.models.governance import TenantIntegration
from app.models.tenant import Tenant, User
from app.schemas.settings import (
    AiAssistSettingsResponse,
    AiAssistSettingsUpdate,
    IdentitySettingsResponse,
    IdentitySettingsUpdate,
    IntegrationSettingsResponse,
    IntegrationSettingsUpdate,
    OrganizationSettingsResponse,
    OrganizationSettingsUpdate,
    GatewaySettingsResponse,
    GatewaySettingsUpdate,
)
from app.services.ai_assist_config_service import ai_assist_status, update_ai_assist_settings
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


@router.get("/settings/ai-assist", response_model=AiAssistSettingsResponse)
async def get_ai_assist_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiAssistSettingsResponse:
    return AiAssistSettingsResponse(**await ai_assist_status(db, current_user.tenant_id))


@router.put("/settings/ai-assist", response_model=AiAssistSettingsResponse)
async def update_ai_assist_settings_route(
    payload: AiAssistSettingsUpdate,
    current_user: Annotated[User, Depends(_require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiAssistSettingsResponse:
    try:
        status_payload = await update_ai_assist_settings(
            db,
            current_user.tenant_id,
            enabled=payload.enabled,
            provider=payload.provider,
            model=payload.model,
            api_key=payload.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AiAssistSettingsResponse(**status_payload)


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
    try:
        updated = await update_tenant_branding(db, tenant, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return OrganizationSettingsResponse(**branding_dict(updated))


@router.get("/settings/identity", response_model=IdentitySettingsResponse)
async def get_identity_settings(
    current_user: Annotated[User, Depends(_require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IdentitySettingsResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one()
    return IdentitySettingsResponse(
        oidc_jit_provision_enabled=tenant.oidc_jit_provision_enabled,
        platform_jit_default=settings.oidc_jit_provision_default,
        allowed_login_domains=tenant.allowed_login_domains,
    )


@router.put("/settings/identity", response_model=IdentitySettingsResponse)
async def update_identity_settings(
    payload: IdentitySettingsUpdate,
    current_user: Annotated[User, Depends(_require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IdentitySettingsResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one()

    if payload.oidc_jit_provision_enabled is not None:
        tenant.oidc_jit_provision_enabled = payload.oidc_jit_provision_enabled
    if payload.allowed_login_domains is not None:
        tenant.allowed_login_domains = payload.allowed_login_domains

    await db.commit()
    await db.refresh(tenant)
    return IdentitySettingsResponse(
        oidc_jit_provision_enabled=tenant.oidc_jit_provision_enabled,
        platform_jit_default=settings.oidc_jit_provision_default,
        allowed_login_domains=tenant.allowed_login_domains,
    )


@router.get("/settings/gateway", response_model=GatewaySettingsResponse)
async def get_gateway_settings(
    current_user: Annotated[User, Depends(_require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GatewaySettingsResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one()
    return GatewaySettingsResponse(
        ai_rate_limit_rpm=tenant.ai_rate_limit_rpm,
        ai_rate_limit_rph=tenant.ai_rate_limit_rph,
        ai_rate_limit_rpd=tenant.ai_rate_limit_rpd,
        ai_token_limit_tpm=tenant.ai_token_limit_tpm,
        ai_token_limit_tph=tenant.ai_token_limit_tph,
        ai_token_limit_tpd=tenant.ai_token_limit_tpd,
        ai_token_budgets=tenant.ai_token_budgets,
        allowed_api_origins=tenant.allowed_api_origins,
        token_saving_enabled=tenant.token_saving_enabled,
        token_saving_mode=tenant.token_saving_mode,
    )


@router.put("/settings/gateway", response_model=GatewaySettingsResponse)
async def update_gateway_settings(
    payload: GatewaySettingsUpdate,
    current_user: Annotated[User, Depends(_require_org_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GatewaySettingsResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one()

    def _normalize(val: int | None) -> int | None:
        return val if val and val > 0 else None

    if payload.ai_rate_limit_rpm is not None:
        tenant.ai_rate_limit_rpm = _normalize(payload.ai_rate_limit_rpm)
    if payload.ai_rate_limit_rph is not None:
        tenant.ai_rate_limit_rph = _normalize(payload.ai_rate_limit_rph)
    if payload.ai_rate_limit_rpd is not None:
        tenant.ai_rate_limit_rpd = _normalize(payload.ai_rate_limit_rpd)
    if payload.ai_token_limit_tpm is not None:
        tenant.ai_token_limit_tpm = _normalize(payload.ai_token_limit_tpm)
    if payload.ai_token_limit_tph is not None:
        tenant.ai_token_limit_tph = _normalize(payload.ai_token_limit_tph)
    if payload.ai_token_limit_tpd is not None:
        tenant.ai_token_limit_tpd = _normalize(payload.ai_token_limit_tpd)
    if payload.ai_token_budgets is not None:
        tenant.ai_token_budgets = payload.ai_token_budgets
    if payload.allowed_api_origins is not None:
        tenant.allowed_api_origins = payload.allowed_api_origins
    if payload.token_saving_enabled is not None:
        tenant.token_saving_enabled = payload.token_saving_enabled
    if payload.token_saving_mode is not None:
        mode = payload.token_saving_mode
        if mode in ("json_to_toon", "strip_markdown", "both"):
            tenant.token_saving_mode = mode

    await db.commit()
    await db.refresh(tenant)
    
    return GatewaySettingsResponse(
        ai_rate_limit_rpm=tenant.ai_rate_limit_rpm,
        ai_rate_limit_rph=tenant.ai_rate_limit_rph,
        ai_rate_limit_rpd=tenant.ai_rate_limit_rpd,
        ai_token_limit_tpm=tenant.ai_token_limit_tpm,
        ai_token_limit_tph=tenant.ai_token_limit_tph,
        ai_token_limit_tpd=tenant.ai_token_limit_tpd,
        ai_token_budgets=tenant.ai_token_budgets,
        allowed_api_origins=tenant.allowed_api_origins,
        token_saving_enabled=tenant.token_saving_enabled,
        token_saving_mode=tenant.token_saving_mode,
    )
