"""global_intents_classifier

Revision ID: 082_global_intents_classifier
Revises: 081_edge_mesh
Create Date: 2026-08-29 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '082_global_intents_classifier'
down_revision: Union[str, None] = '081_edge_mesh'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    # Update custom_intents table if present
    if 'custom_intents' in tables:
        columns = {c['name'] for c in sa.inspect(bind).get_columns('custom_intents')}
        
        # Alter tenant_id to be nullable so global platform rules can have tenant_id = NULL
        op.alter_column('custom_intents', 'tenant_id', nullable=True)

        if 'scope' not in columns:
            op.add_column('custom_intents', sa.Column('scope', sa.String(length=16), server_default='tenant', nullable=False))
        if 'pattern_type' not in columns:
            op.add_column('custom_intents', sa.Column('pattern_type', sa.String(length=32), server_default='keyword', nullable=False))
        if 'regex_pattern' not in columns:
            op.add_column('custom_intents', sa.Column('regex_pattern', sa.String(length=512), nullable=True))
        if 'syntax_rules' not in columns:
            op.add_column('custom_intents', sa.Column('syntax_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        if 'target_tenant_ids' not in columns:
            op.add_column('custom_intents', sa.Column('target_tenant_ids', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))
        if 'is_system' not in columns:
            op.add_column('custom_intents', sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False))
        if 'risk_level' not in columns:
            op.add_column('custom_intents', sa.Column('risk_level', sa.String(length=16), server_default='high', nullable=False))
        if 'explanation_template' not in columns:
            op.add_column('custom_intents', sa.Column('explanation_template', sa.String(length=256), nullable=True))

    # Create classifier_efficiency_metrics table
    if 'classifier_efficiency_metrics' not in tables:
        op.create_table(
            'classifier_efficiency_metrics',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
            sa.Column('total_scans', sa.BigInteger(), server_default='0', nullable=False),
            sa.Column('blocked_count', sa.BigInteger(), server_default='0', nullable=False),
            sa.Column('redacted_count', sa.BigInteger(), server_default='0', nullable=False),
            sa.Column('avg_latency_micros', sa.Float(), server_default='250.0', nullable=False),
            sa.Column('category_breakdown', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
            sa.Column('metric_date', sa.Date(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )
        op.create_index('ix_classifier_metrics_tenant_date', 'classifier_efficiency_metrics', ['tenant_id', 'metric_date'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if 'classifier_efficiency_metrics' in tables:
        op.drop_index('ix_classifier_metrics_tenant_date', table_name='classifier_efficiency_metrics')
        op.drop_table('classifier_efficiency_metrics')

    if 'custom_intents' in tables:
        columns = {c['name'] for c in sa.inspect(bind).get_columns('custom_intents')}
        for col in ['explanation_template', 'risk_level', 'is_system', 'target_tenant_ids', 'syntax_rules', 'regex_pattern', 'pattern_type', 'scope']:
            if col in columns:
                op.drop_column('custom_intents', col)
