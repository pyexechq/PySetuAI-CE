"""trial_requests

Revision ID: 080_trial_requests
Revises: 079_mcp_fields
Create Date: 2026-08-25 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '080_trial_requests'
down_revision: Union[str, None] = '079_mcp_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if 'trial_requests' not in tables:
        op.create_table(
            'trial_requests',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('full_name', sa.String(length=128), nullable=False),
            sa.Column('work_email', sa.String(length=255), nullable=False),
            sa.Column('company_name', sa.String(length=255), nullable=False),
            sa.Column('team_size', sa.String(length=64), nullable=True),
            sa.Column('use_case', sa.String(length=128), nullable=True),
            sa.Column('message', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_trial_requests_work_email', 'trial_requests', ['work_email'])

    if 'client_api_keys' in tables:
        columns = {col["name"] for col in sa.inspect(bind).get_columns("client_api_keys")}
        for col_name in ["ai_rate_limit_rpm", "ai_rate_limit_rph", "ai_rate_limit_rpd", "ai_token_limit_tpm", "ai_token_limit_tph", "ai_token_limit_tpd"]:
            if col_name not in columns:
                op.add_column("client_api_keys", sa.Column(col_name, sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_index('ix_trial_requests_work_email', table_name='trial_requests')
    op.drop_table('trial_requests')
