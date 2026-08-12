"""033 — Tenant rate limits."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "033_tenant_rate_limits"
down_revision: Union[str, None] = "032_usage_hooks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("ai_rate_limit_rpm", sa.Integer(), nullable=True))
    op.add_column("tenants", sa.Column("ai_rate_limit_rph", sa.Integer(), nullable=True))
    op.add_column("tenants", sa.Column("ai_rate_limit_rpd", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "ai_rate_limit_rpd")
    op.drop_column("tenants", "ai_rate_limit_rph")
    op.drop_column("tenants", "ai_rate_limit_rpm")
