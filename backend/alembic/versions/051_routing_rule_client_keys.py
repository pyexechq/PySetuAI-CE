"""051 - Persist per-rule assigned client API keys (BL-088)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "051_routing_rule_client_keys"
down_revision: Union[str, None] = "050_routing_rule_response_format"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "routing_rule_client_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "routing_rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("routing_rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "client_api_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_api_keys.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("routing_rule_id", "client_api_key_id", name="uq_routing_rule_client_key"),
    )


def downgrade() -> None:
    op.drop_table("routing_rule_client_keys")
