"""049 — MCP SSO injection and tool deny rules (BL-084/BL-085)."""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "049_mcp_security_controls"
down_revision: Union[str, None] = "048_request_log_retention"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table("mcp_sso_injection_configs", sa.Column("id", uuid_type, primary_key=True), sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id"), nullable=False), sa.Column("server_id", uuid_type, sa.ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("header_name", sa.String(128), nullable=False, server_default="Authorization"), sa.Column("header_format", sa.String(256), nullable=False, server_default="Bearer {token}"), sa.Column("claim_extract", sa.String(128), nullable=False, server_default=""), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("tenant_id", "server_id", name="uq_mcp_sso_injection_tenant_server"))
    op.create_index("ix_mcp_sso_injection_configs_tenant_id", "mcp_sso_injection_configs", ["tenant_id"])
    op.create_index("ix_mcp_sso_injection_configs_server_id", "mcp_sso_injection_configs", ["server_id"])
    op.create_table("mcp_tool_deny_rules", sa.Column("id", uuid_type, primary_key=True), sa.Column("tenant_id", uuid_type, sa.ForeignKey("tenants.id"), nullable=False), sa.Column("role", sa.String(50), nullable=False), sa.Column("server_id", uuid_type, sa.ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False), sa.Column("tool_name", sa.String(255), nullable=False), sa.Column("reason", sa.String(512), nullable=False, server_default="Explicit deny by admin"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("tenant_id", "role", "server_id", "tool_name", name="uq_mcp_tool_deny_tenant_role_tool"))
    op.create_index("ix_mcp_tool_deny_rules_tenant_id", "mcp_tool_deny_rules", ["tenant_id"])
    op.create_index("ix_mcp_tool_deny_rules_role", "mcp_tool_deny_rules", ["role"])
    op.create_index("ix_mcp_tool_deny_rules_server_id", "mcp_tool_deny_rules", ["server_id"])


def downgrade() -> None:
    op.drop_table("mcp_tool_deny_rules")
    op.drop_table("mcp_sso_injection_configs")