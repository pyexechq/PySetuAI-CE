"""Add token budget columns

Revision ID: 035_token_budgets
Revises: 034_domain_allowlists
Create Date: 2026-08-11 18:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "035_token_budgets"
down_revision: Union[str, None] = "034_domain_allowlists"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("ai_token_limit_tpm", sa.Integer(), nullable=True))
    op.add_column("tenants", sa.Column("ai_token_limit_tph", sa.Integer(), nullable=True))
    op.add_column("tenants", sa.Column("ai_token_limit_tpd", sa.Integer(), nullable=True))
    op.add_column("tenants", sa.Column("ai_token_budgets", JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "ai_token_budgets")
    op.drop_column("tenants", "ai_token_limit_tpd")
    op.drop_column("tenants", "ai_token_limit_tph")
    op.drop_column("tenants", "ai_token_limit_tpm")
