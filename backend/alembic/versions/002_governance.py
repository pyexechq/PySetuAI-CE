"""Phase 2 governance tables

Revision ID: 002_governance
Revises: 001_initial
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_governance"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("policy_type", sa.String(length=50), server_default="folder"),
        sa.Column("status", sa.String(length=20), server_default="active"),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rules", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["policies.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policies_tenant_id", "policies", ["tenant_id"])

    op.create_table(
        "mcp_servers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("success_rate", sa.Float(), server_default="0"),
        sa.Column("avg_latency_ms", sa.Integer(), server_default="0"),
        sa.Column("total_calls", sa.Integer(), server_default="0"),
        sa.Column("trust_score", sa.Float(), server_default="0"),
        sa.Column("risk_score", sa.Float(), server_default="0"),
        sa.Column("status", sa.String(length=20), server_default="healthy"),
        sa.Column("tools_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mcp_servers_tenant_id", "mcp_servers", ["tenant_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("risk", sa.String(length=20), server_default="low"),
        sa.Column("details", sa.Text(), server_default=""),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    op.create_table(
        "llm_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider_type", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("total_requests", sa.Integer(), server_default="0"),
        sa.Column("percentage", sa.Float(), server_default="0"),
        sa.Column("avg_latency_ms", sa.Integer(), server_default="0"),
        sa.Column("success_rate", sa.Float(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_providers_tenant_id", "llm_providers", ["tenant_id"])

    op.create_table(
        "routing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="10"),
        sa.Column("condition", sa.Text(), nullable=False),
        sa.Column("target_model", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_routing_rules_tenant_id", "routing_rules", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_routing_rules_tenant_id", table_name="routing_rules")
    op.drop_table("routing_rules")
    op.drop_index("ix_llm_providers_tenant_id", table_name="llm_providers")
    op.drop_table("llm_providers")
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_mcp_servers_tenant_id", table_name="mcp_servers")
    op.drop_table("mcp_servers")
    op.drop_index("ix_policies_tenant_id", table_name="policies")
    op.drop_table("policies")
