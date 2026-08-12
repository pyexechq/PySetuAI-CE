"""Add custom_intents table

Revision ID: 038_custom_intents
Revises: 037_prompt_templates
Create Date: 2026-08-12 11:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "038_custom_intents"
down_revision: Union[str, None] = "037_prompt_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custom_intents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("action", sa.String(32), nullable=False, server_default="block"),  # block, monitor, redact
        sa.Column("keywords", JSONB, nullable=False, server_default="[]"),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("custom_intents")
