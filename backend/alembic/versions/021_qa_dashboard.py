"""021 — QA dashboard tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "021_qa_dashboard"
down_revision: Union[str, None] = "021_uag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qa_test_cycles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), server_default="planned"),
        sa.Column("release_decision", sa.String(32), server_default="pending"),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by_name", sa.String(255), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )
    op.create_table(
        "qa_test_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("cycle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("qa_test_cycles.id"), nullable=False, index=True),
        sa.Column("case_id", sa.String(32), nullable=False, index=True),
        sa.Column("module", sa.String(100), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("priority", sa.String(8), server_default="P1"),
        sa.Column("method", sa.String(32), server_default="manual"),
        sa.Column("status", sa.String(32), server_default="not_tested"),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("automated_key", sa.String(512), nullable=True),
        sa.Column("tested_by_name", sa.String(255), server_default=""),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "qa_defects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("cycle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("qa_test_cycles.id"), nullable=True),
        sa.Column("linked_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("qa_test_cases.id"), nullable=True),
        sa.Column("defect_code", sa.String(32), nullable=False, index=True),
        sa.Column("severity", sa.String(8), server_default="S3"),
        sa.Column("module", sa.String(100), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("status", sa.String(32), server_default="open"),
        sa.Column("created_by_name", sa.String(255), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("qa_defects")
    op.drop_table("qa_test_cases")
    op.drop_table("qa_test_cycles")
