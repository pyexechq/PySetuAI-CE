"""041 — Token saving tenant settings."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "041_token_saving"
down_revision: Union[str, None] = "040_bundles_intents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("token_saving_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "tenants",
        sa.Column("token_saving_mode", sa.String(length=32), nullable=False, server_default="both"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "token_saving_mode")
    op.drop_column("tenants", "token_saving_enabled")
