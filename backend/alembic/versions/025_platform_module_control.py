"""025 — Lock tenant module visibility to platform operator control."""

from typing import Sequence, Union

from alembic import op

revision: str = "025_platform_module_control"
down_revision: Union[str, None] = "024_tenant_feature_flags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FEATURE_KEYS = ("qa_dashboard", "compatibility_center", "governance_sandbox", "reports")


def upgrade() -> None:
    for key in FEATURE_KEYS:
        op.execute(
            f"""
            UPDATE tenants
            SET feature_policy = jsonb_set(
                COALESCE(feature_policy, '{{}}'::jsonb),
                '{{{key}}}',
                COALESCE(feature_policy->'{key}', '{{}}'::jsonb) || '{{"tenant_editable": false}}'::jsonb,
                true
            )
            """
        )


def downgrade() -> None:
    for key in FEATURE_KEYS:
        op.execute(
            f"""
            UPDATE tenants
            SET feature_policy = jsonb_set(
                COALESCE(feature_policy, '{{}}'::jsonb),
                '{{{key}}}',
                COALESCE(feature_policy->'{key}', '{{}}'::jsonb) || '{{"tenant_editable": true}}'::jsonb,
                true
            )
            """
        )
