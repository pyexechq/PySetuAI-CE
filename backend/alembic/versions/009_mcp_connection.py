"""Add MCP connection fields (endpoint, transport, config)

Revision ID: 009_mcp_connection
Revises: 008_mcp_tool_names
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "009_mcp_connection"
down_revision: Union[str, None] = "008_mcp_tool_names"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mcp_servers", sa.Column("endpoint_url", sa.String(512), nullable=True))
    op.add_column("mcp_servers", sa.Column("transport", sa.String(32), server_default="sse", nullable=False))
    op.add_column("mcp_servers", sa.Column("connection_config", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("mcp_servers", "connection_config")
    op.drop_column("mcp_servers", "transport")
    op.drop_column("mcp_servers", "endpoint_url")
