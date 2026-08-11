"""032 — Gateway usage metering hooks on audit logs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "032_usage_hooks"
down_revision: Union[str, None] = "031_invite_email_tpl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("usage_metadata", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("audit_logs", "usage_metadata")
