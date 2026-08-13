"""048 — Full request/response log retention (BL-073)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "048_request_log_retention"
down_revision: Union[str, None] = "047_mcp_url_filters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("request_log_retention_days", sa.Integer(), nullable=False, server_default="30"),
    )
    op.create_table(
        "audit_log_bodies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("audit_log_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audit_logs.id"), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(), nullable=True),
        sa.Column("response_payload", postgresql.JSONB(), nullable=True),
        sa.Column("guardrail_events", postgresql.JSONB(), nullable=True),
        sa.Column("tool_events", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("audit_log_id", name="uq_audit_log_bodies_audit_log_id"),
    )
    op.create_index("ix_audit_log_bodies_tenant_id", "audit_log_bodies", ["tenant_id"])
    op.create_index("ix_audit_log_bodies_created_at", "audit_log_bodies", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_bodies_created_at", table_name="audit_log_bodies")
    op.drop_index("ix_audit_log_bodies_tenant_id", table_name="audit_log_bodies")
    op.drop_table("audit_log_bodies")
    op.drop_column("tenants", "request_log_retention_days")
