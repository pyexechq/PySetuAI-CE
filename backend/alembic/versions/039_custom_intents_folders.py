"""Add parent_id and intent_type to custom_intents

Revision ID: 039_custom_intents_folders
Revises: 038_custom_intents
Create Date: 2026-08-12 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "039_custom_intents_folders"
down_revision: Union[str, None] = "038_custom_intents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "custom_intents",
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("custom_intents.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    op.add_column(
        "custom_intents",
        sa.Column("intent_type", sa.String(32), nullable=False, server_default="intent"),
    )


def downgrade() -> None:
    op.drop_column("custom_intents", "intent_type")
    op.drop_column("custom_intents", "parent_id")
