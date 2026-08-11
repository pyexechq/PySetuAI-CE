"""016 — Tenant white-label branding columns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_tenant_branding"
down_revision: Union[str, None] = "015_alert_webhooks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("display_name", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("logo_url", sa.String(1024), nullable=True))
    op.add_column("tenants", sa.Column("brand_tagline", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "brand_tagline")
    op.drop_column("tenants", "logo_url")
    op.drop_column("tenants", "display_name")
