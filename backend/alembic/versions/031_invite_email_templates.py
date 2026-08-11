"""031 — Platform invite email templates."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "031_invite_email_tpl"
down_revision: Union[str, None] = "030_tenant_invites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATES = [
    {
        "slug": "professional_welcome",
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
    <p style="margin:0 0 20px;"><a href="{{invite_url}}" style="display:inline-block;padding:12px 20px;background:#2563eb;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;">Accept invite</a></p>
    <p style="margin:0 0 8px;font-size:13px;color:#64748b;">Or copy this link:</p>
    <p style="margin:0 0 20px;font-size:12px;word-break:break-all;color:#334155;">{{invite_url}}</p>
    <p style="margin:0;font-size:12px;color:#64748b;">This invite expires on {{expires_at}}.</p>
  </div>
</body></html>""",
        "text_body": """Hi {{admin_name}},

You've been invited as the tenant administrator for {{tenant_name}} on {{platform_name}}.

Accept your invite:
{{invite_url}}

Tenant workspace: {{tenant_url}}
Expires: {{expires_at}}
""",
    },
    {
        "slug": "warm_onboarding",
        "name": "Warm onboarding",
        "description": "Friendly tone for customer success-led onboarding.",
        "subject": "{{admin_name}}, your {{tenant_name}} workspace is ready",
        "html_body": """<!DOCTYPE html>
<html><body style="font-family:Georgia,serif;background:#fff7ed;padding:24px;color:#431407;">
  <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #fed7aa;border-radius:16px;padding:28px;">
    <h1 style="margin:0 0 12px;font-size:24px;color:#9a3412;">You're almost in</h1>
    <p style="margin:0 0 16px;line-height:1.7;">Hi {{admin_name}},</p>
    <p style="margin:0 0 16px;line-height:1.7;">
      Your team at <strong>{{tenant_name}}</strong> is ready on {{platform_name}}.
      Click below to choose your password and jump into the control plane.
    </p>
    <p style="margin:0 0 20px;"><a href="{{invite_url}}" style="display:inline-block;padding:12px 20px;background:#2563eb;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;">Activate my account</a></p>
    <p style="margin:0 0 8px;font-size:13px;color:#9a3412;">Need the raw link?</p>
    <p style="margin:0 0 20px;font-size:12px;word-break:break-all;">{{invite_url}}</p>
    <p style="margin:0;font-size:12px;color:#9a3412;">Link expires {{expires_at}}.</p>
  </div>
</body></html>""",
        "text_body": """Hi {{admin_name}},

Your {{tenant_name}} workspace is ready on {{platform_name}}.

Activate your account:
{{invite_url}}

Expires: {{expires_at}}
""",
    },
    {
        "slug": "security_first",
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
    <p style="margin:0 0 20px;"><a href="{{invite_url}}" style="display:inline-block;padding:12px 20px;background:#2563eb;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;">Review and accept invite</a></p>
    <p style="margin:0;font-size:11px;color:#94a3b8;word-break:break-all;">{{invite_url}}</p>
  </div>
</body></html>""",
        "text_body": """SECURE ADMIN INVITE — {{tenant_name}}

Recipient: {{admin_email}}
Platform: {{platform_name}}
Expires: {{expires_at}}

Single-use activation link:
{{invite_url}}
""",
    },
]


def upgrade() -> None:
    op.create_table(
        "platform_email_templates",
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("text_body", sa.Text(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("slug"),
    )
    op.create_index("ix_platform_email_templates_category", "platform_email_templates", ["category"])

    template_table = sa.table(
        "platform_email_templates",
        sa.column("slug", sa.String),
        sa.column("category", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("subject", sa.String),
        sa.column("html_body", sa.Text),
        sa.column("text_body", sa.Text),
        sa.column("is_builtin", sa.Boolean),
    )
    op.bulk_insert(
        template_table,
        [
            {
                "slug": item["slug"],
                "category": "tenant_admin_invite",
                "name": item["name"],
                "description": item["description"],
                "subject": item["subject"],
                "html_body": item["html_body"],
                "text_body": item["text_body"],
                "is_builtin": True,
            }
            for item in TEMPLATES
        ],
    )

    op.add_column("tenant_invites", sa.Column("email_template_slug", sa.String(length=100), nullable=True))
    op.add_column("tenant_invites", sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenant_invites", sa.Column("email_delivery_status", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant_invites", "email_delivery_status")
    op.drop_column("tenant_invites", "email_sent_at")
    op.drop_column("tenant_invites", "email_template_slug")
    op.drop_index("ix_platform_email_templates_category", table_name="platform_email_templates")
    op.drop_table("platform_email_templates")
