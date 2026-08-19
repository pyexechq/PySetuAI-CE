"""Tenant OPA data-movement policy configuration."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "060_data_movement_policy"
down_revision: str | None = "059_iac_evidence_tenant_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_integrations",
        sa.Column("data_movement_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_integrations", "data_movement_policy")
