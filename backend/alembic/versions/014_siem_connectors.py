"""SIEM connector table revision 014."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014_siem_connectors"
down_revision: Union[str, None] = "013_audit_ingestion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "siem_connectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("connector_type", sa.String(32), nullable=False, server_default="webhook"),
        sa.Column("endpoint_url", sa.String(1024), nullable=False),
        sa.Column("auth_token", sa.Text(), nullable=True),
        sa.Column("export_format", sa.String(16), nullable=False, server_default="json"),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("events_exported", sa.Integer(), server_default="0"),
        sa.Column("last_export_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("siem_connectors")
