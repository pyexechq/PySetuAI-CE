"""Tenant admin invite tokens for SaaS onboarding."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import get_password_hash
from app.models.tenant import Tenant, TenantInvite, User
from app.services.invite_email_template_service import (
    DEFAULT_TEMPLATE_SLUG,
    send_tenant_invite_email,
)
from app.services.tenant_site_service import tenant_public_url

INVITE_TTL_DAYS = 7


def _invite_accept_path(token: str) -> str:
    return f"/accept-invite?token={token}"


def build_invite_url(token: str, *, tenant_subdomain: str | None = None) -> str:
    if tenant_subdomain:
        base = tenant_public_url(tenant_subdomain)
    else:
        base = settings.frontend_url.rstrip("/")
    return f"{base}{_invite_accept_path(token)}"


def invite_response_dict(
    invite: TenantInvite,
    *,
    tenant: Tenant,
    email_delivery: dict | None = None,
) -> dict:
    subdomain = tenant.subdomain or tenant.slug
    payload = {
        "id": str(invite.id),
        "tenant_id": str(invite.tenant_id),
        "email": invite.email,
        "role": invite.role,
        "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
        "accepted_at": invite.accepted_at.isoformat() if invite.accepted_at else None,
        "invite_url": build_invite_url(invite.token, tenant_subdomain=subdomain),
        "email_template_slug": invite.email_template_slug,
        "email_sent": invite.email_delivery_status == "sent",
        "email_status": invite.email_delivery_status,
        "email_sent_at": invite.email_sent_at.isoformat() if invite.email_sent_at else None,
    }
    if email_delivery:
        payload.update(
            {
                "email_sent": email_delivery.get("email_sent", payload["email_sent"]),
                "email_status": email_delivery.get("email_status", payload["email_status"]),
                "email_template_slug": email_delivery.get("email_template_slug", payload["email_template_slug"]),
                "email_reason": email_delivery.get("email_reason"),
            }
        )
    return payload


async def create_tenant_invite(
    db: AsyncSession,
    *,
    tenant: Tenant,
    email: str,
    role: str = "tenant_admin",
    invited_by_user_id: uuid.UUID | None = None,
    admin_name: str | None = None,
    template_slug: str = DEFAULT_TEMPLATE_SLUG,
    send_email: bool = True,
) -> dict:
    normalized_email = email.strip().lower()
    display_name = (admin_name or normalized_email.split("@", 1)[0]).strip()

    existing_user = await db.execute(
        select(User.id).where(User.tenant_id == tenant.id, User.email == normalized_email)
    )
    if existing_user.scalar_one_or_none() is not None:
        raise ValueError(f"User '{normalized_email}' already exists for this tenant.")

    pending = await db.execute(
        select(TenantInvite).where(
            TenantInvite.tenant_id == tenant.id,
            TenantInvite.email == normalized_email,
            TenantInvite.accepted_at.is_(None),
            TenantInvite.expires_at > datetime.now(UTC),
        )
    )
    active_invite = pending.scalar_one_or_none()
    if active_invite is not None:
        invite = active_invite
    else:
        token = secrets.token_urlsafe(32)
        invite = TenantInvite(
            tenant_id=tenant.id,
            email=normalized_email,
            role=role,
            token=token,
            invited_by_user_id=invited_by_user_id,
            expires_at=datetime.now(UTC) + timedelta(days=INVITE_TTL_DAYS),
        )
        db.add(invite)
        await db.flush()

    invite_url = build_invite_url(invite.token, tenant_subdomain=tenant.subdomain or tenant.slug)
    email_delivery = None
    if send_email:
        email_delivery = await send_tenant_invite_email(
            db,
            tenant=tenant,
            invite=invite,
            invite_url=invite_url,
            admin_name=display_name,
            template_slug=template_slug,
        )

    return invite_response_dict(invite, tenant=tenant, email_delivery=email_delivery)


async def get_invite_preview(db: AsyncSession, token: str) -> dict | None:
    result = await db.execute(
        select(TenantInvite, Tenant)
        .join(Tenant, Tenant.id == TenantInvite.tenant_id)
        .where(TenantInvite.token == token.strip())
    )
    row = result.one_or_none()
    if row is None:
        return None
    invite, tenant = row
    if invite.accepted_at is not None:
        raise ValueError("This invite has already been accepted.")
    if invite.expires_at <= datetime.now(UTC):
        raise ValueError("This invite has expired.")
    if not tenant.is_active:
        raise ValueError("Tenant is suspended.")
    return {
        "email": invite.email,
        "role": invite.role,
        "tenant_name": tenant.name,
        "tenant_slug": tenant.slug,
        "expires_at": invite.expires_at.isoformat(),
    }


async def accept_tenant_invite(
    db: AsyncSession,
    *,
    token: str,
    password: str,
    name: str | None = None,
) -> dict:
    result = await db.execute(
        select(TenantInvite, Tenant)
        .join(Tenant, Tenant.id == TenantInvite.tenant_id)
        .where(TenantInvite.token == token.strip())
    )
    row = result.one_or_none()
    if row is None:
        raise ValueError("Invalid invite token.")
    invite, tenant = row
    if invite.accepted_at is not None:
        raise ValueError("This invite has already been accepted.")
    if invite.expires_at <= datetime.now(UTC):
        raise ValueError("This invite has expired.")
    if not tenant.is_active:
        raise ValueError("Tenant is suspended.")

    user_result = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == invite.email)
    )
    user = user_result.scalar_one_or_none()
    display_name = (name or invite.email.split("@", 1)[0]).strip()
    if user is None:
        user = User(
            tenant_id=tenant.id,
            email=invite.email,
            name=display_name,
            hashed_password=get_password_hash(password),
            role=invite.role,
        )
        db.add(user)
    else:
        user.name = display_name or user.name
        user.hashed_password = get_password_hash(password)
        user.role = invite.role
        user.is_active = True

    invite.accepted_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)
    await db.refresh(tenant)

    from app.core.security import create_access_token

    access_token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "tenant_slug": tenant.slug,
        "tenant_url": tenant_public_url(tenant.subdomain or tenant.slug),
    }
