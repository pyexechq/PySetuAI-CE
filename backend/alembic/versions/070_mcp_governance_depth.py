"""Per-tool MCP policies and MCP tool-chain events for governance depth."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "070_mcp_governance_depth"
down_revision: str | None = "069_policy_file_governance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mcp_tool_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("server_id", sa.UUID(), nullable=False),
        sa.Column("tool_name", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=20), server_default="allow", nullable=False),
        sa.Column("risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reason", sa.String(length=512), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["mcp_servers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "server_id", "tool_name", name="uq_mcp_tool_policy_tenant_server_tool"),
    )
    op.create_index("ix_mcp_tool_policies_tenant_id", "mcp_tool_policies", ["tenant_id"])
    op.create_index("ix_mcp_tool_policies_server_id", "mcp_tool_policies", ["server_id"])

    op.create_table(
        "mcp_tool_chain_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("security_event_id", sa.UUID(), nullable=True),
        sa.Column("approval_request_id", sa.UUID(), nullable=True),
        sa.Column("source_agent_id", sa.UUID(), nullable=True),
        sa.Column("target_agent_id", sa.UUID(), nullable=True),
        sa.Column("endpoint_id", sa.UUID(), nullable=True),
        sa.Column("mcp_server_id", sa.UUID(), nullable=True),
        sa.Column("mcp_server_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("tool_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("tool_risk", sa.String(length=20), server_default="read", nullable=False),
        sa.Column("data_source", sa.String(length=512), server_default="", nullable=False),
        sa.Column("external_service", sa.String(length=512), server_default="", nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("chain_risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=True),
        sa.Column("policy_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mcp_server_id"], ["mcp_servers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["security_event_id"], ["security_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mcp_tool_chain_events_tenant_id", "mcp_tool_chain_events", ["tenant_id"])
    op.create_index("ix_mcp_tool_chain_events_security_event_id", "mcp_tool_chain_events", ["security_event_id"])
    op.create_index("ix_mcp_tool_chain_events_approval_request_id", "mcp_tool_chain_events", ["approval_request_id"])
    op.create_index("ix_mcp_tool_chain_events_source_agent_id", "mcp_tool_chain_events", ["source_agent_id"])
    op.create_index("ix_mcp_tool_chain_events_target_agent_id", "mcp_tool_chain_events", ["target_agent_id"])
    op.create_index("ix_mcp_tool_chain_events_endpoint_id", "mcp_tool_chain_events", ["endpoint_id"])
    op.create_index("ix_mcp_tool_chain_events_mcp_server_id", "mcp_tool_chain_events", ["mcp_server_id"])
    op.create_index("ix_mcp_tool_chain_events_decision", "mcp_tool_chain_events", ["decision"])
    op.create_index("ix_mcp_tool_chain_events_chain_risk_score", "mcp_tool_chain_events", ["chain_risk_score"])
    op.create_index("ix_mcp_tool_chain_events_created_at", "mcp_tool_chain_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_mcp_tool_chain_events_created_at", table_name="mcp_tool_chain_events")
    op.drop_index("ix_mcp_tool_chain_events_chain_risk_score", table_name="mcp_tool_chain_events")
    op.drop_index("ix_mcp_tool_chain_events_decision", table_name="mcp_tool_chain_events")
    op.drop_index("ix_mcp_tool_chain_events_mcp_server_id", table_name="mcp_tool_chain_events")
    op.drop_index("ix_mcp_tool_chain_events_endpoint_id", table_name="mcp_tool_chain_events")
    op.drop_index("ix_mcp_tool_chain_events_target_agent_id", table_name="mcp_tool_chain_events")
    op.drop_index("ix_mcp_tool_chain_events_source_agent_id", table_name="mcp_tool_chain_events")
    op.drop_index("ix_mcp_tool_chain_events_approval_request_id", table_name="mcp_tool_chain_events")
    op.drop_index("ix_mcp_tool_chain_events_security_event_id", table_name="mcp_tool_chain_events")
    op.drop_index("ix_mcp_tool_chain_events_tenant_id", table_name="mcp_tool_chain_events")
    op.drop_table("mcp_tool_chain_events")

    op.drop_index("ix_mcp_tool_policies_server_id", table_name="mcp_tool_policies")
    op.drop_index("ix_mcp_tool_policies_tenant_id", table_name="mcp_tool_policies")
    op.drop_table("mcp_tool_policies")
