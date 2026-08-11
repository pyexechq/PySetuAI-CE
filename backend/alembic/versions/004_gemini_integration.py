"""Add Gemini API key to tenant integrations

Revision ID: 004_gemini_integration
Revises: 003_tenant_integrations
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_gemini_integration"
down_revision: Union[str, None] = "003_tenant_integrations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenant_integrations", sa.Column("gemini_api_key", sa.Text(), nullable=True))
    op.add_column(
        "tenant_integrations",
        sa.Column("gemini_default_model", sa.String(length=255), server_default="gemini-1.5-pro"),
    )


def downgrade() -> None:
    op.drop_column("tenant_integrations", "gemini_default_model")
    op.drop_column("tenant_integrations", "gemini_api_key")
