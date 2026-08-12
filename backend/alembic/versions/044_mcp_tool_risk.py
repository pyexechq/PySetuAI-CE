"""044 — Auto-hide destructive MCP tools tenant setting."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "044_mcp_tool_risk"
down_revision: Union[str, None] = "043_mcp_oauth_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("mcp_auto_hide_destructive", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("tenants", "mcp_auto_hide_destructive")
