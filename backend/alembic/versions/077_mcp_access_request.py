"""mcp access request

Revision ID: 077_mcp_access_request
Revises: 076_sanctioned_ai_tools
Create Date: 2026-08-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '077_mcp_access_request'
down_revision: Union[str, None] = '076_sanctioned_ai_tools'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('approval_requests', sa.Column('requested_mcp_tool', sa.String(length=255), nullable=True))
    op.add_column('approval_requests', sa.Column('requested_bundle_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_approval_requests_requested_bundle_id'), 'approval_requests', ['requested_bundle_id'], unique=False)
    op.create_foreign_key('fk_approval_requests_requested_bundle_id_policy_bundles', 'approval_requests', 'policy_bundles', ['requested_bundle_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_approval_requests_requested_bundle_id_policy_bundles', 'approval_requests', type_='foreignkey')
    op.drop_index(op.f('ix_approval_requests_requested_bundle_id'), table_name='approval_requests')
    op.drop_column('approval_requests', 'requested_bundle_id')
    op.drop_column('approval_requests', 'requested_mcp_tool')
