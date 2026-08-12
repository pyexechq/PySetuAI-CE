"""Add custom_intent_ids to policy_bundles

Revision ID: 040_policy_bundles_custom_intents
Revises: 039_custom_intents_folders
Create Date: 2026-08-12 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "040_bundles_intents"
down_revision: Union[str, None] = "039_custom_intents_folders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "policy_bundles",
        sa.Column("custom_intent_ids", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("policy_bundles", "custom_intent_ids")
