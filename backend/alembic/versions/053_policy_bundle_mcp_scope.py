"""053 — Policy bundle MCP tool scope (allowlist per workload)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "053_policy_bundle_mcp_scope"
down_revision: Union[str, None] = "052_provider_token_costs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("policy_bundles", sa.Column("mcp_scope", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("policy_bundles", "mcp_scope")
