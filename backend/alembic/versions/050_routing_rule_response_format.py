"""050 - Persist per-rule response format (BL-087)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "050_routing_rule_response_format"
down_revision: Union[str, None] = "049_mcp_security_controls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "routing_rules",
        sa.Column("response_format", sa.String(20), nullable=False, server_default="auto"),
    )


def downgrade() -> None:
    op.drop_column("routing_rules", "response_format")