"""027 — Custom LLM provider endpoint URL."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "027_llm_provider_endpoint_url"
down_revision: Union[str, None] = "026_tenant_ai_assist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("llm_providers", sa.Column("endpoint_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("llm_providers", "endpoint_url")
