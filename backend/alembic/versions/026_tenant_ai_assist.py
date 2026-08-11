"""026 — Tenant AI Assist settings (platform-wide AI features API key)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "026_tenant_ai_assist"
down_revision: Union[str, None] = "025_platform_module_control"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant_integrations",
        sa.Column("ai_assist_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "tenant_integrations",
        sa.Column("ai_assist_provider", sa.String(length=32), nullable=False, server_default="openai"),
    )
    op.add_column(
        "tenant_integrations",
        sa.Column("ai_assist_model", sa.String(length=255), nullable=False, server_default="gpt-4o-mini"),
    )
    op.add_column("tenant_integrations", sa.Column("ai_assist_api_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant_integrations", "ai_assist_api_key")
    op.drop_column("tenant_integrations", "ai_assist_model")
    op.drop_column("tenant_integrations", "ai_assist_provider")
    op.drop_column("tenant_integrations", "ai_assist_enabled")
