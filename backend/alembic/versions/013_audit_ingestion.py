"""Audit log ingestion columns revision 013."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_audit_ingestion"
down_revision: Union[str, None] = "012_compliance_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column("source", sa.String(64), server_default="internal", nullable=False),
    )
    op.add_column(
        "audit_logs",
        sa.Column("external_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_audit_logs_source", "audit_logs", ["source"])
    op.create_index(
        "uq_audit_logs_tenant_source_external_id",
        "audit_logs",
        ["tenant_id", "source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_audit_logs_tenant_source_external_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_source", table_name="audit_logs")
    op.drop_column("audit_logs", "external_id")
    op.drop_column("audit_logs", "source")
