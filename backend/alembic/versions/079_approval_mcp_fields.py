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
    op.add_column('approval_requests', sa.Column('requested_mcp_tool', sa.String(255), nullable=True))
    op.add_column('approval_requests', sa.Column('requested_bundle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('policy_bundles.id', ondelete='SET NULL'), nullable=True))


def downgrade() -> None:
    op.drop_column('approval_requests', 'requested_bundle_id')
    op.drop_column('approval_requests', 'requested_mcp_tool')
