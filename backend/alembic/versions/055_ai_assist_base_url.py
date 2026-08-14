"""Add ai_assist_base_url for local OpenAI-compatible AI Assist providers."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "055_ai_assist_base_url"
down_revision: str | None = "054_client_api_key_token_saving"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_integrations",
        sa.Column("ai_assist_base_url", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_integrations", "ai_assist_base_url")
