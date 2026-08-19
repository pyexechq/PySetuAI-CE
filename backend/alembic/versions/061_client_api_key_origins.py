"""Per-key allowed API origins on client_api_keys."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "061_client_api_key_origins"
down_revision: str | None = "060_data_movement_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "client_api_keys",
        sa.Column("allowed_api_origins", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("client_api_keys", "allowed_api_origins")
