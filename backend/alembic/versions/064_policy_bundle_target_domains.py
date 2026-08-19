"""Target domains on policy_bundles, for browser-extension site scoping."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "064_policy_bundle_target_domains"
down_revision: str | None = "063_incident_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "policy_bundles",
        sa.Column("target_domains", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("policy_bundles", "target_domains")
