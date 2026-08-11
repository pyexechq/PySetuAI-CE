"""Add schedule recipients to report definitions

Revision ID: 006_report_schedule_recipients
Revises: 005_report_definitions
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_report_schedule_recipients"
down_revision: Union[str, None] = "005_report_definitions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report_definitions",
        sa.Column("schedule_recipients", postgresql.JSONB(), server_default="[]", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("report_definitions", "schedule_recipients")
