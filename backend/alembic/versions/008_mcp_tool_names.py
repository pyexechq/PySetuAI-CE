"""Add tool_names JSONB to mcp_servers

Revision ID: 008_mcp_tool_names
Revises: 007_report_generation_status
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "008_mcp_tool_names"
down_revision: Union[str, None] = "007_report_generation_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mcp_servers", sa.Column("tool_names", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("mcp_servers", "tool_names")
