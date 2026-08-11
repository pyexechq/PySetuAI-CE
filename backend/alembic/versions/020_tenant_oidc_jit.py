"""020 — Per-tenant OIDC JIT provisioning toggle."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020_tenant_oidc_jit"
down_revision: Union[str, None] = "019_tenant_site_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("oidc_jit_provision_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("tenants", "oidc_jit_provision_enabled")
