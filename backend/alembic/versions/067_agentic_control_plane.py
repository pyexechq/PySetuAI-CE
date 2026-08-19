"""Endpoint, agent, capability, and security-event tables for the agent control plane."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "067_agentic_control_plane"
down_revision: str | None = "066_client_api_key_encrypted"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "endpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("os_name", sa.String(length=64), server_default="", nullable=False),
        sa.Column("os_version", sa.String(length=128), server_default="", nullable=False),
        sa.Column("agent_version", sa.String(length=64), server_default="", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "hostname", name="uq_endpoints_tenant_hostname"),
    )
    op.create_index("ix_endpoints_tenant_id", "endpoints", ["tenant_id"])
    op.create_index("ix_endpoints_status", "endpoints", ["status"])
    op.create_index("ix_endpoints_last_seen_at", "endpoints", ["last_seen_at"])

    op.create_table(
        "agents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("endpoint_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("agent_type", sa.String(length=64), nullable=False),
        sa.Column("vendor", sa.String(length=128), server_default="", nullable=False),
        sa.Column("version", sa.String(length=64), server_default="", nullable=False),
        sa.Column("user_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("data_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tools", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("mcp_servers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "endpoint_id", "name", name="uq_agents_tenant_endpoint_name"),
    )
    op.create_index("ix_agents_tenant_id", "agents", ["tenant_id"])
    op.create_index("ix_agents_endpoint_id", "agents", ["endpoint_id"])
    op.create_index("ix_agents_agent_type", "agents", ["agent_type"])
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_index("ix_agents_last_activity_at", "agents", ["last_activity_at"])

    op.create_table(
        "agent_capabilities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("capability_type", sa.String(length=64), nullable=False),
        sa.Column("resource_pattern", sa.String(length=512), server_default="", nullable=False),
        sa.Column("name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_capabilities_tenant_id", "agent_capabilities", ["tenant_id"])
    op.create_index("ix_agent_capabilities_agent_id", "agent_capabilities", ["agent_id"])

    op.create_table(
        "security_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("endpoint_id", sa.UUID(), nullable=True),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column("audit_log_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.String(length=64), server_default="endpoint", nullable=False),
        sa.Column("event_type", sa.String(length=64), server_default="agent", nullable=False),
        sa.Column("user_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("tool", sa.String(length=255), server_default="", nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource", sa.String(length=1024), server_default="", nullable=False),
        sa.Column("classification", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=True),
        sa.Column("policy_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["audit_log_id"], ["audit_logs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_events_tenant_id", "security_events", ["tenant_id"])
    op.create_index("ix_security_events_endpoint_id", "security_events", ["endpoint_id"])
    op.create_index("ix_security_events_agent_id", "security_events", ["agent_id"])
    op.create_index("ix_security_events_audit_log_id", "security_events", ["audit_log_id"])
    op.create_index("ix_security_events_source", "security_events", ["source"])
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_action", "security_events", ["action"])
    op.create_index("ix_security_events_decision", "security_events", ["decision"])
    op.create_index("ix_security_events_risk_score", "security_events", ["risk_score"])
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_security_events_created_at", table_name="security_events")
    op.drop_index("ix_security_events_risk_score", table_name="security_events")
    op.drop_index("ix_security_events_decision", table_name="security_events")
    op.drop_index("ix_security_events_action", table_name="security_events")
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_index("ix_security_events_source", table_name="security_events")
    op.drop_index("ix_security_events_audit_log_id", table_name="security_events")
    op.drop_index("ix_security_events_agent_id", table_name="security_events")
    op.drop_index("ix_security_events_endpoint_id", table_name="security_events")
    op.drop_index("ix_security_events_tenant_id", table_name="security_events")
    op.drop_table("security_events")

    op.drop_index("ix_agent_capabilities_agent_id", table_name="agent_capabilities")
    op.drop_index("ix_agent_capabilities_tenant_id", table_name="agent_capabilities")
    op.drop_table("agent_capabilities")

    op.drop_index("ix_agents_last_activity_at", table_name="agents")
    op.drop_index("ix_agents_status", table_name="agents")
    op.drop_index("ix_agents_agent_type", table_name="agents")
    op.drop_index("ix_agents_endpoint_id", table_name="agents")
    op.drop_index("ix_agents_tenant_id", table_name="agents")
    op.drop_table("agents")

    op.drop_index("ix_endpoints_last_seen_at", table_name="endpoints")
    op.drop_index("ix_endpoints_status", table_name="endpoints")
    op.drop_index("ix_endpoints_tenant_id", table_name="endpoints")
    op.drop_table("endpoints")
