"""Microsoft Copilot governance: instances, connectors, baselines, and drift."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "071_copilot_governance"
down_revision: str | None = "070_mcp_governance_depth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "copilot_instances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("instance_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("owner", sa.String(length=255), server_default="", nullable=False),
        sa.Column("environment", sa.String(length=128), server_default="", nullable=False),
        sa.Column("data_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_copilot_instances_tenant_external"),
    )
    op.create_index("ix_copilot_instances_tenant_id", "copilot_instances", ["tenant_id"])
    op.create_index("ix_copilot_instances_instance_type", "copilot_instances", ["instance_type"])
    op.create_index("ix_copilot_instances_status", "copilot_instances", ["status"])
    op.create_index("ix_copilot_instances_last_synced_at", "copilot_instances", ["last_synced_at"])

    op.create_table(
        "copilot_connectors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("connector_type", sa.String(length=32), nullable=False),
        sa.Column("publisher", sa.String(length=255), server_default="", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("risk_band", sa.String(length=20), server_default="low", nullable=False),
        sa.Column("auth_type", sa.String(length=64), server_default="", nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("data_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_copilot_connectors_tenant_external"),
    )
    op.create_index("ix_copilot_connectors_tenant_id", "copilot_connectors", ["tenant_id"])
    op.create_index("ix_copilot_connectors_connector_type", "copilot_connectors", ["connector_type"])
    op.create_index("ix_copilot_connectors_status", "copilot_connectors", ["status"])
    op.create_index("ix_copilot_connectors_last_synced_at", "copilot_connectors", ["last_synced_at"])

    op.create_table(
        "copilot_baselines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("created_by", sa.String(length=255), server_default="", nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_copilot_baselines_tenant_id", "copilot_baselines", ["tenant_id"])
    op.create_index("ix_copilot_baselines_created_at", "copilot_baselines", ["created_at"])

    op.create_table(
        "copilot_drift_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("baseline_id", sa.UUID(), nullable=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("entity_external_id", sa.String(length=255), server_default="", nullable=False),
        sa.Column("entity_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("drift_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("previous_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("current_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["baseline_id"], ["copilot_baselines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_copilot_drift_records_tenant_id", "copilot_drift_records", ["tenant_id"])
    op.create_index("ix_copilot_drift_records_baseline_id", "copilot_drift_records", ["baseline_id"])
    op.create_index("ix_copilot_drift_records_entity_type", "copilot_drift_records", ["entity_type"])
    op.create_index("ix_copilot_drift_records_drift_type", "copilot_drift_records", ["drift_type"])
    op.create_index("ix_copilot_drift_records_severity", "copilot_drift_records", ["severity"])
    op.create_index("ix_copilot_drift_records_status", "copilot_drift_records", ["status"])
    op.create_index("ix_copilot_drift_records_created_at", "copilot_drift_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_copilot_drift_records_created_at", table_name="copilot_drift_records")
    op.drop_index("ix_copilot_drift_records_status", table_name="copilot_drift_records")
    op.drop_index("ix_copilot_drift_records_severity", table_name="copilot_drift_records")
    op.drop_index("ix_copilot_drift_records_drift_type", table_name="copilot_drift_records")
    op.drop_index("ix_copilot_drift_records_entity_type", table_name="copilot_drift_records")
    op.drop_index("ix_copilot_drift_records_baseline_id", table_name="copilot_drift_records")
    op.drop_index("ix_copilot_drift_records_tenant_id", table_name="copilot_drift_records")
    op.drop_table("copilot_drift_records")

    op.drop_index("ix_copilot_baselines_created_at", table_name="copilot_baselines")
    op.drop_index("ix_copilot_baselines_tenant_id", table_name="copilot_baselines")
    op.drop_table("copilot_baselines")

    op.drop_index("ix_copilot_connectors_last_synced_at", table_name="copilot_connectors")
    op.drop_index("ix_copilot_connectors_status", table_name="copilot_connectors")
    op.drop_index("ix_copilot_connectors_connector_type", table_name="copilot_connectors")
    op.drop_index("ix_copilot_connectors_tenant_id", table_name="copilot_connectors")
    op.drop_table("copilot_connectors")

    op.drop_index("ix_copilot_instances_last_synced_at", table_name="copilot_instances")
    op.drop_index("ix_copilot_instances_status", table_name="copilot_instances")
    op.drop_index("ix_copilot_instances_instance_type", table_name="copilot_instances")
    op.drop_index("ix_copilot_instances_tenant_id", table_name="copilot_instances")
    op.drop_table("copilot_instances")
