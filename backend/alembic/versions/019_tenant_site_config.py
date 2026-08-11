"""019 — Tenant public site configuration (subdomain + entry mode)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019_tenant_site_config"
down_revision: Union[str, None] = "018_oidc_user_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("subdomain", sa.String(100), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("entry_mode", sa.String(32), nullable=False, server_default="login_only"),
    )
    op.execute("UPDATE tenants SET subdomain = slug WHERE subdomain IS NULL")
    op.create_index("ix_tenants_subdomain", "tenants", ["subdomain"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tenants_subdomain", table_name="tenants")
    op.drop_column("tenants", "entry_mode")
    op.drop_column("tenants", "subdomain")
