"""018 — OIDC user identity columns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_oidc_user_identity"
down_revision: Union[str, None] = "017_tenant_oidc_providers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_provider", sa.String(32), nullable=False, server_default="local"))
    op.add_column("users", sa.Column("external_subject", sa.String(512), nullable=True))
    op.create_index(
        "ix_users_tenant_oidc_subject",
        "users",
        ["tenant_id", "auth_provider", "external_subject"],
        unique=True,
        postgresql_where=sa.text("external_subject IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_tenant_oidc_subject", table_name="users")
    op.drop_column("users", "external_subject")
    op.drop_column("users", "auth_provider")
