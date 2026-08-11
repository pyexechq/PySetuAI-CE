"""028 — UAG tenant client response protocol settings."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "028_uag_client_response"
down_revision: Union[str, None] = "027_llm_provider_endpoint_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant_integrations",
        sa.Column("uag_client_protocol", sa.String(length=32), server_default="openai", nullable=False),
    )
    op.add_column(
        "tenant_integrations",
        sa.Column("uag_include_metadata", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("tenant_integrations", "uag_include_metadata")
    op.drop_column("tenant_integrations", "uag_client_protocol")
