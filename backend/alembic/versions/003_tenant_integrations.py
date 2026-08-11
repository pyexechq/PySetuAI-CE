"""Tenant integration settings

Revision ID: 003_tenant_integrations
Revises: 002_governance
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_tenant_integrations"
down_revision: Union[str, None] = "002_governance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("openai_api_key", sa.Text(), nullable=True),
        sa.Column("ollama_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ollama_base_url", sa.String(length=512), server_default="http://localhost:11434"),
        sa.Column("ollama_default_model", sa.String(length=255), server_default="llama3.2"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_integrations_tenant_id"),
    )
    op.create_index("ix_tenant_integrations_tenant_id", "tenant_integrations", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_tenant_integrations_tenant_id", table_name="tenant_integrations")
    op.drop_table("tenant_integrations")
