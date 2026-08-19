"""Tenant IaC evidence scanner configuration."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "059_iac_evidence_tenant_config"
down_revision: str | None = "058_policy_exemptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_integrations",
        sa.Column("iac_scan_paths", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "tenant_integrations",
        sa.Column("iac_checks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_integrations", "iac_checks")
    op.drop_column("tenant_integrations", "iac_scan_paths")
