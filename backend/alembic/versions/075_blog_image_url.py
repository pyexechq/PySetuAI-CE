"""Add optional image_url to blog articles."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "075_blog_image_url"
down_revision: str | None = "074_framework_rule_packs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "blog_articles",
        sa.Column("image_url", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("blog_articles", "image_url")
