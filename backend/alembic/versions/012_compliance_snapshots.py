"""Compliance evidence snapshots revision 012."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_compliance_snapshots"
down_revision: Union[str, None] = "011_policy_bundles_client_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compliance_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by_name", sa.String(255), server_default=""),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overall_score", sa.Float(), server_default="0"),
        sa.Column("frameworks_compliant", sa.Integer(), server_default="0"),
        sa.Column("frameworks_total", sa.Integer(), server_default="0"),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("frameworks", postgresql.JSONB(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("compliance_snapshots")
