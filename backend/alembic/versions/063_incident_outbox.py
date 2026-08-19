"""Incident outbox dedup and connector JSON on alert_webhooks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "063_incident_outbox"
down_revision: str | None = "062_client_api_key_byok"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "alert_webhooks",
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "alert_webhooks",
        sa.Column("dispatch_policy_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "alert_webhooks",
        sa.Column("tickets_created", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_table(
        "incident_outbox",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("connector_id", sa.UUID(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("external_ticket_id", sa.String(length=255), nullable=False),
        sa.Column("external_url", sa.String(length=1024), nullable=True),
        sa.Column("event_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("first_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["alert_webhooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incident_outbox_tenant_id", "incident_outbox", ["tenant_id"])
    op.create_index("ix_incident_outbox_connector_id", "incident_outbox", ["connector_id"])
    op.create_index("ix_incident_outbox_fingerprint", "incident_outbox", ["fingerprint"])
    op.create_index(
        "ix_incident_outbox_dedup",
        "incident_outbox",
        ["tenant_id", "connector_id", "fingerprint", "last_event_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_incident_outbox_dedup", table_name="incident_outbox")
    op.drop_index("ix_incident_outbox_fingerprint", table_name="incident_outbox")
    op.drop_index("ix_incident_outbox_connector_id", table_name="incident_outbox")
    op.drop_index("ix_incident_outbox_tenant_id", table_name="incident_outbox")
    op.drop_table("incident_outbox")
    op.drop_column("alert_webhooks", "tickets_created")
    op.drop_column("alert_webhooks", "dispatch_policy_json")
    op.drop_column("alert_webhooks", "config_json")
