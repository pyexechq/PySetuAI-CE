"""edge_gateway_nodes

Revision ID: 081_edge_mesh
Revises: 080_trial_requests
Create Date: 2026-08-27 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '081_edge_mesh'
down_revision: Union[str, None] = '080_trial_requests'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if 'edge_gateway_nodes' not in tables:
        op.create_table(
            'edge_gateway_nodes',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
            sa.Column('node_id', sa.String(length=64), nullable=False),
            sa.Column('name', sa.String(length=128), nullable=False),
            sa.Column('region', sa.String(length=64), server_default='us-east-1', nullable=False),
            sa.Column('cloud_provider', sa.String(length=64), server_default='aws', nullable=False),
            sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
            sa.Column('ip_address', sa.String(length=64), nullable=True),
            sa.Column('hostname', sa.String(length=255), nullable=True),
            sa.Column('enrollment_token_hash', sa.String(length=255), nullable=False),
            sa.Column('bundle_version', sa.Integer(), server_default='1', nullable=False),
            sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('sync_latency_ms', sa.Float(), server_default='1.2', nullable=False),
            sa.Column('requests_routed_24h', sa.Integer(), server_default='0', nullable=False),
            sa.Column('cpu_percent', sa.Float(), server_default='12.5', nullable=True),
            sa.Column('memory_percent', sa.Float(), server_default='24.0', nullable=True),
            sa.Column('meta_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_edge_gateway_nodes_node_id', 'edge_gateway_nodes', ['node_id'], unique=True)
        op.create_index('ix_edge_gateway_nodes_region', 'edge_gateway_nodes', ['region'])
        op.create_index('ix_edge_gateway_nodes_status', 'edge_gateway_nodes', ['status'])
        op.create_index('ix_edge_gateway_nodes_tenant_id', 'edge_gateway_nodes', ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_edge_gateway_nodes_tenant_id', table_name='edge_gateway_nodes')
    op.drop_index('ix_edge_gateway_nodes_status', table_name='edge_gateway_nodes')
    op.drop_index('ix_edge_gateway_nodes_region', table_name='edge_gateway_nodes')
    op.drop_index('ix_edge_gateway_nodes_node_id', table_name='edge_gateway_nodes')
    op.drop_table('edge_gateway_nodes')
