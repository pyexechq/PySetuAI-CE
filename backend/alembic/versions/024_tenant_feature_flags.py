"""024 — Tenant feature flags for platform-managed module entitlements."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "024_tenant_feature_flags"
down_revision: Union[str, None] = "023_uag_backfill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "feature_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "feature_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.execute(
        """
        UPDATE tenants
        SET feature_flags = jsonb_build_object('qa_dashboard', qa_dashboard_enabled)
        WHERE qa_dashboard_enabled = false
        """
    )
    op.execute(
        """
        UPDATE tenants
        SET feature_policy = jsonb_set(
            COALESCE(feature_policy, '{}'::jsonb),
            '{qa_dashboard}',
            '{"tenant_editable": false}'::jsonb,
            true
        )
        WHERE qa_dashboard_enabled = false
        """
    )


def downgrade() -> None:
    op.drop_column("tenants", "feature_policy")
    op.drop_column("tenants", "feature_flags")
