import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_tenant, get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.tenant import Tenant, User
from app.schemas.auth import (
    DashboardMetricsResponse,
    LoginRequest,
    TenantBrandingPublicResponse,
    TenantPublicSiteResponse,
    TenantResponse,
    TokenResponse,
    UserResponse,
)
from app.schemas.dashboard import DashboardMetricInsightResponse, DashboardOverviewResponse
from app.services.dashboard_metric_insights_service import build_metric_insight
from app.schemas.oidc import OidcAuthorizeResponse, OidcCallbackRequest, OidcPublicProviderResponse
from app.services.dashboard_service import build_dashboard_overview
from app.services.oidc_auth_service import begin_oidc_login, complete_oidc_login
from app.services.oidc_provider_service import list_public_providers, public_provider_dict
from app.services.tenant_branding_service import public_branding_dict
from app.services.tenant_features_service import feature_flags_for_api, feature_policy_for_api
from app.services.tenant_site_service import resolve_public_site

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenResponse:
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.slug == payload.tenant_slug, Tenant.is_active.is_(True))
    )
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_result = await db.execute(
        select(User).where(
            User.tenant_id == tenant.id,
            User.email == payload.email.lower(),
            User.is_active.is_(True),
        )
    )
    user = user_result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        tenant_id=str(current_user.tenant_id),
    )


@router.get("/tenants/current", response_model=TenantResponse)
async def get_tenant(current_tenant: Annotated[Tenant, Depends(get_current_tenant)]) -> TenantResponse:
    return TenantResponse(
        id=str(current_tenant.id),
        name=current_tenant.name,
        slug=current_tenant.slug,
        display_name=current_tenant.display_name,
        logo_url=current_tenant.logo_url,
        brand_tagline=current_tenant.brand_tagline,
        qa_dashboard_enabled=feature_flags_for_api(current_tenant)["qa_dashboard"],
        features=feature_flags_for_api(current_tenant),
        feature_policy=feature_policy_for_api(current_tenant),
    )


@router.get("/tenants/branding/{tenant_slug}", response_model=TenantBrandingPublicResponse)
async def get_tenant_branding(
    tenant_slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantBrandingPublicResponse:
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug.strip().lower(), Tenant.is_active.is_(True))
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantBrandingPublicResponse(**public_branding_dict(tenant))


@router.get("/tenants/site-config", response_model=TenantPublicSiteResponse)
async def get_tenant_site_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    subdomain: str | None = Query(default=None, max_length=100),
    slug: str | None = Query(default=None, max_length=100),
    host: str | None = Query(default=None, max_length=255),
) -> TenantPublicSiteResponse:
    site = await resolve_public_site(db, subdomain=subdomain, slug=slug, host=host)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant site not found")
    return TenantPublicSiteResponse(**site)


@router.get("/auth/oidc/providers", response_model=list[OidcPublicProviderResponse])
async def list_public_oidc_providers(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_slug: str = Query(..., min_length=1, max_length=100),
) -> list[OidcPublicProviderResponse]:
    providers = await list_public_providers(db, tenant_slug)
    return [OidcPublicProviderResponse(**public_provider_dict(p)) for p in providers]


@router.get("/auth/oidc/authorize", response_model=OidcAuthorizeResponse)
async def start_oidc_login(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_slug: str = Query(..., min_length=1, max_length=100),
    provider_id: str = Query(..., min_length=1),
) -> OidcAuthorizeResponse:
    try:
        provider_uuid = uuid.UUID(provider_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider id") from exc

    try:
        result = await begin_oidc_login(db, tenant_slug=tenant_slug, provider_id=provider_uuid)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OIDC discovery failed: {exc}") from exc

    return OidcAuthorizeResponse(
        authorization_url=result.authorization_url,
        state=result.state,
        provider_name=result.provider_name,
    )


@router.post("/auth/oidc/callback", response_model=TokenResponse)
async def finish_oidc_login(
    payload: OidcCallbackRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    try:
        result = await complete_oidc_login(db, code=payload.code, state=payload.state)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OIDC token exchange failed: {exc}") from exc

    return TokenResponse(access_token=result.access_token)


@router.get("/dashboard/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardMetricsResponse:
    overview = await build_dashboard_overview(db, current_user.tenant_id)
    return overview.metrics


@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardOverviewResponse:
    return await build_dashboard_overview(db, current_user.tenant_id)


@router.get("/dashboard/metrics/{metric_key}/insights", response_model=DashboardMetricInsightResponse)
async def get_dashboard_metric_insights(
    metric_key: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardMetricInsightResponse:
    try:
        return await build_metric_insight(db, current_user.tenant_id, metric_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
