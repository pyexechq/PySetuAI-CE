"""approval_mcp_fields

Revision ID: 079_mcp_fields
Revises: 078_mcp_tools
Create Date: 2026-08-25 00:27:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '079_mcp_fields'
down_revision: Union[str, None] = '078_mcp_tools'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

