"""Unified AI Agent Control Plane models.

These extend the existing governance model (``MCPServer``, ``LLMProvider``, ``AuditLog``)
with endpoint, agent, capability, and normalized security-event records. Endpoint and agent
identity is tenant-scoped and never relies on display names alone.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.tenant import Base


class Endpoint(Base):
    __tablename__ = "endpoints"
    __table_args__ = (UniqueConstraint("tenant_id", "hostname", name="uq_endpoints_tenant_hostname"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    os_name: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    os_version: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    agent_version: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, default=dict)


class AgentInventory(Base):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("tenant_id", "endpoint_id", "name", name="uq_agents_tenant_endpoint_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    endpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    vendor: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    version: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    user_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data_sources: Mapped[list | None] = mapped_column(JSONB, default=list)
    tools: Mapped[list | None] = mapped_column(JSONB, default=list)
    mcp_servers: Mapped[list | None] = mapped_column(JSONB, default=list)
    permissions: Mapped[list | None] = mapped_column(JSONB, default=list)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AgentCapability(Base):
    __tablename__ = "agent_capabilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True
    )
    capability_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_pattern: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    endpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    audit_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_logs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(64), default="endpoint", nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), default="agent", nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    tool: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    classification: Mapped[list | None] = mapped_column(JSONB, default=list)
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    policy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    security_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    endpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    tool: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    classification: Mapped[list | None] = mapped_column(JSONB, default=list)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    policy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    decided_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class MCPToolChainEvent(Base):
    __tablename__ = "mcp_tool_chain_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    security_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approval_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    endpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mcp_server_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mcp_server_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    tool_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    tool_risk: Mapped[str] = mapped_column(String(20), default="read", nullable=False)
    data_source: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    external_service: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    chain_risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    policy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
