"""Admin invite email templates — samples, customization, preview, and delivery."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import PlatformEmailTemplate, Tenant, TenantInvite
from app.services.email_service import send_email
from app.services.tenant_site_service import tenant_public_url

INVITE_TEMPLATE_CATEGORY = "tenant_admin_invite"
DEFAULT_TEMPLATE_SLUG = "professional_welcome"

INVITE_TEMPLATE_VARIABLES = [
    "tenant_name",
    "admin_name",
    "admin_email",
    "invite_url",
    "expires_at",
    "platform_name",
    "tenant_url",
]

_BUTTON_STYLE = (
    "display:inline-block;padding:12px 20px;background:#2563eb;color:#ffffff;"
    "text-decoration:none;border-radius:8px;font-weight:600;"
)

_BUILTIN_TEMPLATES: dict[str, dict[str, str]] = {
    "professional_welcome": {
        "name": "Professional welcome",
        "description": "Clean corporate invite with a primary call-to-action button.",
        "subject": "You're invited to administer {{tenant_name}} on {{platform_name}}",
        "html_body": """<!DOCTYPE html>
<html><body style="font-family:Segoe UI,sans-serif;background:#f8fafc;padding:24px;color:#0f172a;">
  <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:28px;">
    <p style="margin:0 0 12px;font-size:14px;color:#64748b;">{{platform_name}}</p>
    <h1 style="margin:0 0 16px;font-size:22px;">Welcome to {{tenant_name}}</h1>
    <p style="margin:0 0 16px;line-height:1.6;">Hi {{admin_name}},</p>
    <p style="margin:0 0 16px;line-height:1.6;">
      You've been invited as the tenant administrator for <strong>{{tenant_name}}</strong>.
      Use the secure link below to activate your account and set your password.
    </p>
    <p style="margin:0 0 20px;"><a href="{{invite_url}}" style="{{button_style}}">Accept invite</a></p>
    <p style="margin:0 0 8px;font-size:13px;color:#64748b;">Or copy this link:</p>
    <p style="margin:0 0 20px;font-size:12px;word-break:break-all;color:#334155;">{{invite_url}}</p>
    <p style="margin:0;font-size:12px;color:#64748b;">This invite expires on {{expires_at}}.</p>
  </div>
</body></html>""".replace("{{button_style}}", _BUTTON_STYLE),
        "text_body": """Hi {{admin_name}},

You've been invited as the tenant administrator for {{tenant_name}} on {{platform_name}}.

Accept your invite:
{{invite_url}}

Tenant workspace: {{tenant_url}}
Expires: {{expires_at}}
""",
    },
    "warm_onboarding": {
        "name": "Warm onboarding",
        "description": "Friendly tone for customer success-led onboarding.",
        "subject": "{{admin_name}}, your {{tenant_name}} workspace is ready",
        "html_body": """<!DOCTYPE html>
<html><body style="font-family:Georgia,serif;background:#fff7ed;padding:24px;color:#431407;">
  <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #fed7aa;border-radius:16px;padding:28px;">
    <h1 style="margin:0 0 12px;font-size:24px;color:#9a3412;">You're almost in 🎉</h1>
    <p style="margin:0 0 16px;line-height:1.7;">Hi {{admin_name}},</p>
    <p style="margin:0 0 16px;line-height:1.7;">
      Your team at <strong>{{tenant_name}}</strong> is ready on {{platform_name}}.
      Click below to choose your password and jump into the control plane.
    </p>
    <p style="margin:0 0 20px;"><a href="{{invite_url}}" style="{{button_style}}">Activate my account</a></p>
    <p style="margin:0 0 8px;font-size:13px;color:#9a3412;">Need the raw link?</p>
    <p style="margin:0 0 20px;font-size:12px;word-break:break-all;">{{invite_url}}</p>
    <p style="margin:0;font-size:12px;color:#9a3412;">Link expires {{expires_at}}.</p>
  </div>
</body></html>""".replace("{{button_style}}", _BUTTON_STYLE),
        "text_body": """Hi {{admin_name}},

Your {{tenant_name}} workspace is ready on {{platform_name}}.

Activate your account:
{{invite_url}}

Expires: {{expires_at}}
""",
    },
    "security_first": {
        "name": "Security-first",
        "description": "Emphasizes expiry, single-use activation, and tenant isolation.",
        "subject": "Secure administrator invite — {{tenant_name}}",
        "html_body": """<!DOCTYPE html>
<html><body style="font-family:Consolas,monospace;background:#020617;padding:24px;color:#e2e8f0;">
  <div style="max-width:560px;margin:0 auto;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:28px;">
    <p style="margin:0 0 8px;font-size:12px;color:#94a3b8;letter-spacing:0.08em;">SECURE ADMIN INVITE</p>
    <h1 style="margin:0 0 16px;font-size:20px;color:#f8fafc;">{{tenant_name}}</h1>
    <p style="margin:0 0 12px;line-height:1.6;font-family:Segoe UI,sans-serif;">
      Recipient: {{admin_email}}<br/>
      Platform: {{platform_name}}<br/>
      Expires: {{expires_at}}
    </p>
    <p style="margin:0 0 16px;line-height:1.6;font-family:Segoe UI,sans-serif;">
      This single-use link lets {{admin_name}} set credentials for the isolated tenant workspace.
    </p>
    <p style="margin:0 0 20px;"><a href="{{invite_url}}" style="{{button_style}}">Review and accept invite</a></p>
    <p style="margin:0;font-size:11px;color:#94a3b8;word-break:break-all;">{{invite_url}}</p>
  </div>
</body></html>""".replace("{{button_style}}", _BUTTON_STYLE),
        "text_body": """SECURE ADMIN INVITE — {{tenant_name}}

Recipient: {{admin_email}}
Platform: {{platform_name}}
Expires: {{expires_at}}

Single-use activation link:
{{invite_url}}
""",
    },
}


def render_template_string(template: str, context: dict[str, str]) -> str:
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def build_invite_email_context(
    *,
    tenant: Tenant,
    invite: TenantInvite,
    admin_name: str,
    invite_url: str,
) -> dict[str, str]:
    expires = invite.expires_at.astimezone(UTC).strftime("%B %d, %Y %H:%M UTC")
    return {
        "tenant_name": tenant.display_name or tenant.name,
        "admin_name": admin_name.strip() or invite.email.split("@", 1)[0],
        "admin_email": invite.email,
        "invite_url": invite_url,
        "expires_at": expires,
        "platform_name": settings.app_name,
        "tenant_url": tenant_public_url(tenant.subdomain or tenant.slug),
    }


def sample_preview_context() -> dict[str, str]:
    return {
        "tenant_name": "Globex Industries",
        "admin_name": "Alex Admin",
        "admin_email": "alex.admin@globex.com",
        "invite_url": "https://globex.localhost:3000/accept-invite?token=sample-token",
        "expires_at": datetime.now(UTC).strftime("%B %d, %Y %H:%M UTC"),
        "platform_name": settings.app_name,
        "tenant_url": "https://globex.localhost:3000",
    }


def template_dict(row: PlatformEmailTemplate) -> dict[str, Any]:
    return {
        "slug": row.slug,
        "name": row.name,
        "description": row.description,
        "subject": row.subject,
        "html_body": row.html_body,
        "text_body": row.text_body,
        "category": row.category,
        "is_builtin": row.is_builtin,
        "variables": INVITE_TEMPLATE_VARIABLES,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


async def list_invite_email_templates(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        select(PlatformEmailTemplate)
        .where(PlatformEmailTemplate.category == INVITE_TEMPLATE_CATEGORY)
        .order_by(PlatformEmailTemplate.name.asc())
    )
    return [template_dict(row) for row in result.scalars().all()]


async def get_invite_email_template(db: AsyncSession, slug: str) -> dict[str, Any] | None:
    result = await db.execute(
        select(PlatformEmailTemplate).where(
            PlatformEmailTemplate.slug == slug,
            PlatformEmailTemplate.category == INVITE_TEMPLATE_CATEGORY,
        )
    )
    row = result.scalar_one_or_none()
    return template_dict(row) if row else None


async def update_invite_email_template(
    db: AsyncSession,
    slug: str,
    *,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> dict[str, Any] | None:
    result = await db.execute(
        select(PlatformEmailTemplate).where(
            PlatformEmailTemplate.slug == slug,
            PlatformEmailTemplate.category == INVITE_TEMPLATE_CATEGORY,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    row.subject = subject.strip()
    row.html_body = html_body
    row.text_body = (text_body or _html_to_plain_fallback(html_body)).strip()
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return template_dict(row)


async def reset_invite_email_template(db: AsyncSession, slug: str) -> dict[str, Any] | None:
    builtin = _BUILTIN_TEMPLATES.get(slug)
    if builtin is None:
        return None
    return await update_invite_email_template(
        db,
        slug,
        subject=builtin["subject"],
        html_body=builtin["html_body"],
        text_body=builtin["text_body"],
    )


async def preview_invite_email(
    db: AsyncSession,
    *,
    template_slug: str,
    context: dict[str, str] | None = None,
) -> dict[str, str]:
    template = await get_invite_email_template(db, template_slug)
    if template is None:
        raise ValueError(f"Unknown invite email template '{template_slug}'.")
    merge_context = sample_preview_context()
    if context:
        merge_context.update({key: str(value) for key, value in context.items() if value is not None})
    return {
        "template_slug": template_slug,
        "subject": render_template_string(template["subject"], merge_context),
        "html_body": render_template_string(template["html_body"], merge_context),
        "text_body": render_template_string(template["text_body"], merge_context),
    }


async def send_tenant_invite_email(
    db: AsyncSession,
    *,
    tenant: Tenant,
    invite: TenantInvite,
    invite_url: str,
    admin_name: str,
    template_slug: str = DEFAULT_TEMPLATE_SLUG,
) -> dict[str, Any]:
    preview = await preview_invite_email(
        db,
        template_slug=template_slug,
        context=build_invite_email_context(
            tenant=tenant,
            invite=invite,
            admin_name=admin_name,
            invite_url=invite_url,
        ),
    )
    delivery = send_email(
        recipients=[invite.email],
        subject=preview["subject"],
        html_body=preview["html_body"],
        text_body=preview["text_body"],
    )
    invite.email_template_slug = template_slug
    invite.email_delivery_status = delivery["status"]
    if delivery["status"] == "sent":
        invite.email_sent_at = datetime.now(UTC)
    await db.flush()
    return {
        "email_sent": delivery["status"] == "sent",
        "email_status": delivery["status"],
        "email_template_slug": template_slug,
        "email_reason": delivery.get("reason"),
    }


def _html_to_plain_fallback(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.I | re.S)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</?(p|div|li|tr|h[1-6])[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
