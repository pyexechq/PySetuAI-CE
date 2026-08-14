"""054 — Per client API key token saving settings."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "054_client_api_key_token_saving"
down_revision: Union[str, None] = "053_policy_bundle_mcp_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in inspect(bind).get_columns("client_api_keys")}
    if "token_saving_enabled" not in columns:
        op.add_column("client_api_keys", sa.Column("token_saving_enabled", sa.Boolean(), nullable=True))
    if "token_saving_mode" not in columns:
        op.add_column(
            "client_api_keys",
            sa.Column("token_saving_mode", sa.String(length=32), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in inspect(bind).get_columns("client_api_keys")}
    if "token_saving_mode" in columns:
        op.drop_column("client_api_keys", "token_saving_mode")
    if "token_saving_enabled" in columns:
        op.drop_column("client_api_keys", "token_saving_enabled")
