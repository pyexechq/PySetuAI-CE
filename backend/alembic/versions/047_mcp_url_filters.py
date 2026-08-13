"""047 — MCP web search URL filter policy."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "047_mcp_url_filters"
down_revision: Union[str, None] = "046_mcp_portal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT = (
    '{"enabled": true, "mode": "denylist", "patterns": ["*.onion", "localhost", "127.0.0.1"], '
    '"block_private_ips": true, "web_search_enabled": true, "vendor": "none", "vendor_endpoint": ""}'
)


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "mcp_url_filters",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text(f"'{_DEFAULT}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "mcp_url_filters")
