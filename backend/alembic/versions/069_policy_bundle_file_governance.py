"""File governance rules on policy_bundles, for endpoint-agent enforcement."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "069_policy_file_governance"
down_revision: str | None = "068_approval_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if _column_exists("policy_bundles", "file_governance_rules"):
        return
    op.add_column(
        "policy_bundles",
        sa.Column("file_governance_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    if _column_exists("policy_bundles", "file_governance_rules"):
        op.drop_column("policy_bundles", "file_governance_rules")
