"""Time-bound policy exemptions for governed data movement."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "058_policy_exemptions"
down_revision: str | None = "057_genai_dlp_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    return table in inspect(bind).get_table_names()


def upgrade() -> None:
    if not _has_table("policy_exemptions"):
        op.create_table(
            "policy_exemptions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("created_by", sa.String(255), server_default=""),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("ticket_ref", sa.String(128), nullable=True),
            sa.Column("allowed_destinations", postgresql.JSONB(), server_default='["embedding", "llm"]'),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("use_count", sa.Integer(), server_default="0"),
            sa.Column("max_uses", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        )


def downgrade() -> None:
    if _has_table("policy_exemptions"):
        op.drop_table("policy_exemptions")
