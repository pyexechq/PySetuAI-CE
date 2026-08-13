"""052 — Per-model estimated cost per 1M input/output tokens."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "052_provider_token_costs"
down_revision: Union[str, None] = "051_routing_rule_client_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_providers",
        sa.Column("cost_per_1m_input", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "llm_providers",
        sa.Column("cost_per_1m_output", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("llm_providers", "cost_per_1m_output")
    op.drop_column("llm_providers", "cost_per_1m_input")
