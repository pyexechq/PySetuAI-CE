"""017 — Tenant OIDC provider configurations."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017_tenant_oidc_providers"
down_revision: Union[str, None] = "016_tenant_branding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_oidc_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuer_url", sa.String(1024), nullable=False),
        sa.Column("client_id", sa.String(512), nullable=False),
        sa.Column("client_secret", sa.Text(), nullable=True),
        sa.Column("scopes", sa.String(512), nullable=False, server_default="openid profile email"),
        sa.Column("redirect_uri", sa.String(1024), nullable=False),
        sa.Column("role_claim", sa.String(128), nullable=False, server_default="groups"),
        sa.Column("role_mapping", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("tenant_oidc_providers")
