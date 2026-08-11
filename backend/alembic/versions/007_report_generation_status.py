"""Add report generation status and last run result cache

Revision ID: 007_report_generation_status
Revises: 006_report_schedule_recipients
Create Date: 2026-08-10

"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_report_generation_status"
down_revision: Union[str, None] = "006_report_schedule_recipients"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_definitions",
        sa.Column("generation_status", sa.String(length=20), nullable=False, server_default="idle"),
    )
    op.add_column(
        "report_definitions",
        sa.Column("last_run_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("report_definitions", "last_run_result")
    op.drop_column("report_definitions", "generation_status")
