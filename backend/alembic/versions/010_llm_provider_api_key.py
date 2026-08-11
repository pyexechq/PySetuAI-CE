"""Add api_key to llm_providers

Revision ID: 010_llm_provider_api_key
Revises: 009_mcp_connection
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_llm_provider_api_key"
down_revision: Union[str, None] = "009_mcp_connection"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("llm_providers", sa.Column("api_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("llm_providers", "api_key")
