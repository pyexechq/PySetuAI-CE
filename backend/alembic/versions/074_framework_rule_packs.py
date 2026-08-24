"""Add missing policy_bundles.framework_rule_packs column (schema drift fix)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "074_framework_rule_packs"
down_revision: str | None = "073_blog_articles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "policy_bundles",
        sa.Column("framework_rule_packs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("policy_bundles", "framework_rule_packs")
