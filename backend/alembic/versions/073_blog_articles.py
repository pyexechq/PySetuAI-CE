"""Blog articles for the SaaS marketing site, managed by platform admins."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "073_blog_articles"
down_revision: str | None = "072_advanced_agentic_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blog_articles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("excerpt", sa.Text(), server_default="", nullable=False),
        sa.Column("category", sa.String(length=32), server_default="Feature", nullable=False),
        sa.Column("feature", sa.String(length=255), server_default="", nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_time", sa.String(length=32), server_default="5 min read", nullable=False),
        sa.Column("author", sa.String(length=255), server_default="PySetu AI Team", nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("published", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blog_articles_slug", "blog_articles", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_blog_articles_slug", table_name="blog_articles")
    op.drop_table("blog_articles")
