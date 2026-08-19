"""Backfill protected AI domains for existing policy bundles."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "065_backfill_ext_domains"
down_revision: str | None = "064_policy_bundle_target_domains"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE policy_bundles "
            "SET target_domains = '[\"chatgpt.com\", \"gemini.google.com\", \"claude.ai\"]'::jsonb "
            "WHERE target_domains IS NULL"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("UPDATE policy_bundles SET target_domains = NULL"))