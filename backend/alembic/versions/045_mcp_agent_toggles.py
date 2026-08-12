"""045 — Per-agent MCP access toggles."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "045_mcp_agent_toggles"
down_revision: Union[str, None] = "044_mcp_tool_risk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "mcp_agent_toggles",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text(
                '\'{"claude": true, "openai": true, "gemini": true, "cursor": true, "unknown": true}\'::jsonb'
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "mcp_agent_toggles")
