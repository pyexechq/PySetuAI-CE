"""Advanced agentic security: anomalies, prompt-injection findings, exfiltration, guardian actions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "072_advanced_agentic_security"
down_revision: str | None = "071_copilot_governance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_anomaly_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column("endpoint_id", sa.UUID(), nullable=True),
        sa.Column("anomaly_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("baseline_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("observed_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("source_event_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_anomaly_records_tenant_id", "agent_anomaly_records", ["tenant_id"])
    op.create_index("ix_agent_anomaly_records_agent_id", "agent_anomaly_records", ["agent_id"])
    op.create_index("ix_agent_anomaly_records_endpoint_id", "agent_anomaly_records", ["endpoint_id"])
    op.create_index("ix_agent_anomaly_records_anomaly_type", "agent_anomaly_records", ["anomaly_type"])
    op.create_index("ix_agent_anomaly_records_severity", "agent_anomaly_records", ["severity"])
    op.create_index("ix_agent_anomaly_records_risk_score", "agent_anomaly_records", ["risk_score"])
    op.create_index("ix_agent_anomaly_records_status", "agent_anomaly_records", ["status"])
    op.create_index("ix_agent_anomaly_records_created_at", "agent_anomaly_records", ["created_at"])

    op.create_table(
        "prompt_injection_findings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column("endpoint_id", sa.UUID(), nullable=True),
        sa.Column("scan_target_type", sa.String(length=32), nullable=False),
        sa.Column("scan_target", sa.String(length=1024), server_default="", nullable=False),
        sa.Column("content_preview", sa.Text(), server_default="", nullable=False),
        sa.Column("highest_severity", sa.String(length=20), server_default="low", nullable=False),
        sa.Column("detected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("recommended_action", sa.String(length=20), server_default="allow", nullable=False),
        sa.Column("matches", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_injection_findings_tenant_id", "prompt_injection_findings", ["tenant_id"])
    op.create_index("ix_prompt_injection_findings_agent_id", "prompt_injection_findings", ["agent_id"])
    op.create_index("ix_prompt_injection_findings_endpoint_id", "prompt_injection_findings", ["endpoint_id"])
    op.create_index("ix_prompt_injection_findings_scan_target_type", "prompt_injection_findings", ["scan_target_type"])
    op.create_index("ix_prompt_injection_findings_highest_severity", "prompt_injection_findings", ["highest_severity"])
    op.create_index("ix_prompt_injection_findings_status", "prompt_injection_findings", ["status"])
    op.create_index("ix_prompt_injection_findings_created_at", "prompt_injection_findings", ["created_at"])

    op.create_table(
        "exfiltration_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column("endpoint_id", sa.UUID(), nullable=True),
        sa.Column("exfil_type", sa.String(length=32), nullable=False),
        sa.Column("resource", sa.String(length=1024), server_default="", nullable=False),
        sa.Column("tool", sa.String(length=255), server_default="", nullable=False),
        sa.Column("bytes_read", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("event_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("window_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sensitivity", sa.String(length=20), server_default="", nullable=False),
        sa.Column("risk_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("source_event_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_exfiltration_events_tenant_id", "exfiltration_events", ["tenant_id"])
    op.create_index("ix_exfiltration_events_agent_id", "exfiltration_events", ["agent_id"])
    op.create_index("ix_exfiltration_events_endpoint_id", "exfiltration_events", ["endpoint_id"])
    op.create_index("ix_exfiltration_events_exfil_type", "exfiltration_events", ["exfil_type"])
    op.create_index("ix_exfiltration_events_risk_score", "exfiltration_events", ["risk_score"])
    op.create_index("ix_exfiltration_events_status", "exfiltration_events", ["status"])
    op.create_index("ix_exfiltration_events_created_at", "exfiltration_events", ["created_at"])

    op.create_table(
        "guardian_actions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column("endpoint_id", sa.UUID(), nullable=True),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("trigger_id", sa.UUID(), nullable=True),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("action_status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=True),
        sa.Column("policy_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("details", sa.Text(), server_default="", nullable=False),
        sa.Column("execution_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guardian_actions_tenant_id", "guardian_actions", ["tenant_id"])
    op.create_index("ix_guardian_actions_agent_id", "guardian_actions", ["agent_id"])
    op.create_index("ix_guardian_actions_endpoint_id", "guardian_actions", ["endpoint_id"])
    op.create_index("ix_guardian_actions_trigger_type", "guardian_actions", ["trigger_type"])
    op.create_index("ix_guardian_actions_action_type", "guardian_actions", ["action_type"])
    op.create_index("ix_guardian_actions_action_status", "guardian_actions", ["action_status"])
    op.create_index("ix_guardian_actions_created_at", "guardian_actions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_guardian_actions_created_at", table_name="guardian_actions")
    op.drop_index("ix_guardian_actions_action_status", table_name="guardian_actions")
    op.drop_index("ix_guardian_actions_action_type", table_name="guardian_actions")
    op.drop_index("ix_guardian_actions_trigger_type", table_name="guardian_actions")
    op.drop_index("ix_guardian_actions_endpoint_id", table_name="guardian_actions")
    op.drop_index("ix_guardian_actions_agent_id", table_name="guardian_actions")
    op.drop_index("ix_guardian_actions_tenant_id", table_name="guardian_actions")
    op.drop_table("guardian_actions")

    op.drop_index("ix_exfiltration_events_created_at", table_name="exfiltration_events")
    op.drop_index("ix_exfiltration_events_status", table_name="exfiltration_events")
    op.drop_index("ix_exfiltration_events_risk_score", table_name="exfiltration_events")
    op.drop_index("ix_exfiltration_events_exfil_type", table_name="exfiltration_events")
    op.drop_index("ix_exfiltration_events_endpoint_id", table_name="exfiltration_events")
    op.drop_index("ix_exfiltration_events_agent_id", table_name="exfiltration_events")
    op.drop_index("ix_exfiltration_events_tenant_id", table_name="exfiltration_events")
    op.drop_table("exfiltration_events")

    op.drop_index("ix_prompt_injection_findings_created_at", table_name="prompt_injection_findings")
    op.drop_index("ix_prompt_injection_findings_status", table_name="prompt_injection_findings")
    op.drop_index("ix_prompt_injection_findings_highest_severity", table_name="prompt_injection_findings")
    op.drop_index("ix_prompt_injection_findings_scan_target_type", table_name="prompt_injection_findings")
    op.drop_index("ix_prompt_injection_findings_endpoint_id", table_name="prompt_injection_findings")
    op.drop_index("ix_prompt_injection_findings_agent_id", table_name="prompt_injection_findings")
    op.drop_index("ix_prompt_injection_findings_tenant_id", table_name="prompt_injection_findings")
    op.drop_table("prompt_injection_findings")

    op.drop_index("ix_agent_anomaly_records_created_at", table_name="agent_anomaly_records")
    op.drop_index("ix_agent_anomaly_records_status", table_name="agent_anomaly_records")
    op.drop_index("ix_agent_anomaly_records_risk_score", table_name="agent_anomaly_records")
    op.drop_index("ix_agent_anomaly_records_severity", table_name="agent_anomaly_records")
    op.drop_index("ix_agent_anomaly_records_anomaly_type", table_name="agent_anomaly_records")
    op.drop_index("ix_agent_anomaly_records_endpoint_id", table_name="agent_anomaly_records")
    op.drop_index("ix_agent_anomaly_records_agent_id", table_name="agent_anomaly_records")
    op.drop_index("ix_agent_anomaly_records_tenant_id", table_name="agent_anomaly_records")
    op.drop_table("agent_anomaly_records")
