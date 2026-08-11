"""Add report definitions table

Revision ID: 005_report_definitions
Revises: 004_gemini_integration
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_report_definitions"
down_revision: Union[str, None] = "004_gemini_integration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("format", sa.String(length=20), server_default="CSV"),
        sa.Column("query", postgresql.JSONB(), server_default="{}"),
        sa.Column("schedule_frequency", sa.String(length=20), server_default="on_demand"),
        sa.Column("schedule_enabled", sa.Boolean(), server_default="false"),
        sa.Column("schedule_time", sa.String(length=5), server_default="09:00"),
        sa.Column("schedule_day_of_week", sa.Integer(), nullable=True),
        sa.Column("schedule_day_of_month", sa.Integer(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_report_definitions_tenant_id", "report_definitions", ["tenant_id"])
    op.create_index("ix_report_definitions_slug", "report_definitions", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_report_definitions_slug", table_name="report_definitions")
    op.drop_index("ix_report_definitions_tenant_id", table_name="report_definitions")
    op.drop_table("report_definitions")
