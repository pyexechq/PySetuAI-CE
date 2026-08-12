"""042 — Dynamic MCP tool calling tenant settings."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "042_dynamic_tool_calling"
down_revision: Union[str, None] = "041_token_saving"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("dynamic_tool_calling_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "tenants",
        sa.Column("dynamic_tool_max", sa.Integer(), nullable=False, server_default="8"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "dynamic_tool_max")
    op.drop_column("tenants", "dynamic_tool_calling_enabled")
