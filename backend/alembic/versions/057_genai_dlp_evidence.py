"""GenAI evidence bundles and Pinecone integration settings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "057_genai_dlp_evidence"
down_revision: str | None = "056_routing_provider_aliases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {col["name"] for col in inspect(bind).get_columns(table)}


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    return table in inspect(bind).get_table_names()


def upgrade() -> None:
    if not _has_table("genai_evidence_bundles"):
        op.create_table(
            "genai_evidence_bundles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("actor", sa.String(255), server_default=""),
            sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        )

    if not _has_column("tenant_integrations", "pinecone_enabled"):
        op.add_column("tenant_integrations", sa.Column("pinecone_enabled", sa.Boolean(), server_default="false"))
    if not _has_column("tenant_integrations", "pinecone_api_key"):
        op.add_column("tenant_integrations", sa.Column("pinecone_api_key", sa.Text(), nullable=True))
    if not _has_column("tenant_integrations", "pinecone_host"):
        op.add_column(
            "tenant_integrations",
            sa.Column("pinecone_host", sa.String(512), server_default=""),
        )
    if not _has_column("tenant_integrations", "pinecone_namespace"):
        op.add_column(
            "tenant_integrations",
            sa.Column("pinecone_namespace", sa.String(255), server_default=""),
        )
    if not _has_column("tenant_integrations", "pinecone_dimension"):
        op.add_column("tenant_integrations", sa.Column("pinecone_dimension", sa.Integer(), server_default="1536"))


def downgrade() -> None:
    if _has_column("tenant_integrations", "pinecone_dimension"):
        op.drop_column("tenant_integrations", "pinecone_dimension")
    if _has_column("tenant_integrations", "pinecone_namespace"):
        op.drop_column("tenant_integrations", "pinecone_namespace")
    if _has_column("tenant_integrations", "pinecone_host"):
        op.drop_column("tenant_integrations", "pinecone_host")
    if _has_column("tenant_integrations", "pinecone_api_key"):
        op.drop_column("tenant_integrations", "pinecone_api_key")
    if _has_column("tenant_integrations", "pinecone_enabled"):
        op.drop_column("tenant_integrations", "pinecone_enabled")
    if _has_table("genai_evidence_bundles"):
        op.drop_table("genai_evidence_bundles")
