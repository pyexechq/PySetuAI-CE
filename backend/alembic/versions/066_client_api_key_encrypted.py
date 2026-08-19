"""Store encrypted client API key for admin reveal."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "066_client_api_key_encrypted"
down_revision: str | None = "065_backfill_ext_domains"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("client_api_keys", sa.Column("key_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("client_api_keys", "key_encrypted")
