"""BYOK mirrored ingress keys on client_api_keys."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "062_client_api_key_byok"
down_revision: str | None = "061_client_api_key_origins"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "client_api_keys",
        sa.Column("key_source", sa.String(length=16), server_default="pysetu", nullable=False),
    )
    op.add_column(
        "client_api_keys",
        sa.Column("upstream_pass_through", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index("ix_client_api_keys_key_hash_unique", "client_api_keys", ["key_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_client_api_keys_key_hash_unique", table_name="client_api_keys")
    op.drop_column("client_api_keys", "upstream_pass_through")
    op.drop_column("client_api_keys", "key_source")
