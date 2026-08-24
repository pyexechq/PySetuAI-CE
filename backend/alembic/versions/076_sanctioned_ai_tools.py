"""Tenant allowlist of sanctioned AI tools, used to classify endpoint tool discoveries as shadow AI."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "076_sanctioned_ai_tools"
down_revision: str | None = "075_blog_image_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sanctioned_ai_tools",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("added_by", sa.String(length=255), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_sanctioned_ai_tools_tenant_name"),
    )
    op.create_index("ix_sanctioned_ai_tools_tenant_id", "sanctioned_ai_tools", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_sanctioned_ai_tools_tenant_id", table_name="sanctioned_ai_tools")
    op.drop_table("sanctioned_ai_tools")
