"""023 — Backfill UAG tables when DB skipped revision 021_uag."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "023_uag_backfill"
down_revision: Union[str, None] = "022_tenant_qa_dashboard_enabled"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("uag_model_mappings"):
        op.create_table(
            "uag_model_mappings",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("requested_model", sa.String(128), nullable=False),
            sa.Column("actual_model", sa.String(128), nullable=False),
            sa.Column("target_provider", sa.String(64), nullable=False, server_default="openai"),
            sa.Column("emulate_protocol", sa.String(64), nullable=False, server_default="openai"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_uag_model_mappings_tenant", "uag_model_mappings", ["tenant_id"])

    if not _table_exists("uag_translation_policies"):
        op.create_table(
            "uag_translation_policies",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("conditions", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("actions", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_uag_translation_policies_tenant", "uag_translation_policies", ["tenant_id"])

    if not _table_exists("uag_translation_events"):
        op.create_table(
            "uag_translation_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("request_id", sa.String(64), nullable=False),
            sa.Column("source_protocol", sa.String(64), nullable=False),
            sa.Column("target_provider", sa.String(64), nullable=False),
            sa.Column("requested_model", sa.String(128), nullable=False),
            sa.Column("translated_model", sa.String(128), nullable=False),
            sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0"),
            sa.Column("compatibility_score", sa.Float(), nullable=True),
            sa.Column("details", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_uag_translation_events_tenant", "uag_translation_events", ["tenant_id"])
        op.create_index("ix_uag_translation_events_created", "uag_translation_events", ["created_at"])


def downgrade() -> None:
    if _table_exists("uag_translation_events"):
        op.drop_index("ix_uag_translation_events_created", table_name="uag_translation_events")
        op.drop_index("ix_uag_translation_events_tenant", table_name="uag_translation_events")
        op.drop_table("uag_translation_events")
    if _table_exists("uag_translation_policies"):
        op.drop_index("ix_uag_translation_policies_tenant", table_name="uag_translation_policies")
        op.drop_table("uag_translation_policies")
    if _table_exists("uag_model_mappings"):
        op.drop_index("ix_uag_model_mappings_tenant", table_name="uag_model_mappings")
        op.drop_table("uag_model_mappings")
