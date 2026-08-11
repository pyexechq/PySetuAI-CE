"""022 — Tenant-level QA Dashboard visibility toggle."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022_tenant_qa_dashboard_enabled"
down_revision: Union[str, None] = "021_qa_dashboard"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("qa_dashboard_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("tenants", "qa_dashboard_enabled")
