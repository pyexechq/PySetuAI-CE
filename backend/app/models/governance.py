import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.tenant import Base


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(50), default="folder")
    status: Mapped[str] = mapped_column(String(20), default="active")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=True)
    rules: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_calls: Mapped[int] = mapped_column(Integer, default=0)
    trust_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="healthy")
    tools_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_names: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    endpoint_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    transport: Mapped[str] = mapped_column(String(32), default="sse")
    connection_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class McpOAuthCredential(Base):
    __tablename__ = "mcp_oauth_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), unique=True, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    grant_type: Mapped[str] = mapped_column(String(32), default="client_credentials")
    token_url: Mapped[str] = mapped_column(String(1024), default="")
    client_id: Mapped[str] = mapped_column(String(512), default="")
    scopes: Mapped[str] = mapped_column(String(1024), default="")
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserMcpConnection(Base):
    __tablename__ = "user_mcp_connections"
    __table_args__ = (UniqueConstraint("user_id", "server_id", name="uq_user_mcp_connections_user_server"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), index=True
    )
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class McpSsoInjectionConfig(Base):
    __tablename__ = "mcp_sso_injection_configs"
    __table_args__ = (UniqueConstraint("tenant_id", "server_id", name="uq_mcp_sso_injection_tenant_server"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    server_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    header_name: Mapped[str] = mapped_column(String(128), default="Authorization", nullable=False)
    header_format: Mapped[str] = mapped_column(String(256), default="Bearer {token}", nullable=False)
    claim_extract: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class McpToolDenyRule(Base):
    __tablename__ = "mcp_tool_deny_rules"
    __table_args__ = (UniqueConstraint("tenant_id", "role", "server_id", "tool_name", name="uq_mcp_tool_deny_tenant_role_tool"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    server_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), index=True)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), default="Explicit deny by admin", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MCPToolPolicy(Base):
    __tablename__ = "mcp_tool_policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "server_id", "tool_name", name="uq_mcp_tool_policy_tenant_server_tool"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(20), default="allow", nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    risk: Mapped[str] = mapped_column(String(20), default="low")
    details: Mapped[str] = mapped_column(Text, default="")
    usage_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="internal", index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AuditLogBody(Base):
    __tablename__ = "audit_log_bodies"
    __table_args__ = (UniqueConstraint("audit_log_id", name="uq_audit_log_bodies_audit_log_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    audit_log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("audit_logs.id"), index=True)
    request_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    guardrail_events: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_events: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class SiemConnector(Base):
    __tablename__ = "siem_connectors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(32), default="webhook")
    endpoint_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    auth_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    export_format: Mapped[str] = mapped_column(String(16), default="json")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    events_exported: Mapped[int] = mapped_column(Integer, default=0)
    last_export_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertWebhook(Base):
    __tablename__ = "alert_webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_type: Mapped[str] = mapped_column(String(32), default="slack")
    endpoint_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    auth_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(128), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    alerts_sent: Mapped[int] = mapped_column(Integer, default=0)
    last_alert_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    config_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dispatch_policy_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tickets_created: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IncidentOutbox(Base):
    __tablename__ = "incident_outbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alert_webhooks.id", ondelete="CASCADE"), index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_ticket_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, default=1)
    first_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    percentage: Mapped[float] = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_per_1m_input: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_per_1m_output: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    model_aliases: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=10)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    target_model: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    response_format: Mapped[str] = mapped_column(String(20), default="auto", server_default="auto")
    target_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RoutingRuleClientKey(Base):
    __tablename__ = "routing_rule_client_keys"
    __table_args__ = (UniqueConstraint("routing_rule_id", "client_api_key_id", name="uq_routing_rule_client_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    routing_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routing_rules.id", ondelete="CASCADE"), index=True
    )
    client_api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client_api_keys.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PolicyBundle(Base):
    __tablename__ = "policy_bundles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_ids: Mapped[list] = mapped_column(JSONB, default=list)
    custom_intent_ids: Mapped[list] = mapped_column(JSONB, default=list)
    mcp_scope: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    target_domains: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    file_governance_rules: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClientApiKey(Base):
    __tablename__ = "client_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policy_bundles.id"), nullable=True
    )
    client_response_protocol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    
    ai_rate_limit_rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_rate_limit_rph: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_rate_limit_rpd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_token_limit_tpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_token_limit_tph: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_token_limit_tpd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_saving_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    token_saving_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    allowed_api_origins: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    key_source: Mapped[str] = mapped_column(String(16), default="pysetu", server_default="pysetu")
    upstream_pass_through: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComplianceSnapshot(Base):
    __tablename__ = "compliance_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by_name: Mapped[str] = mapped_column(String(255), default="")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    frameworks_compliant: Mapped[int] = mapped_column(Integer, default=0)
    frameworks_total: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    frameworks: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class TenantIntegration(Base):
    __tablename__ = "tenant_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), unique=True, index=True)
    openai_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    gemini_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    gemini_default_model: Mapped[str] = mapped_column(String(255), default="gemini-1.5-pro")
    ollama_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ollama_base_url: Mapped[str] = mapped_column(String(512), default="http://localhost:11434")
    ollama_default_model: Mapped[str] = mapped_column(String(255), default="llama3.2")
    ai_assist_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_assist_provider: Mapped[str] = mapped_column(String(32), default="openai")
    ai_assist_model: Mapped[str] = mapped_column(String(255), default="gpt-4o-mini")
    ai_assist_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_assist_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    uag_client_protocol: Mapped[str] = mapped_column(String(32), default="openai")
    uag_include_metadata: Mapped[bool] = mapped_column(Boolean, default=False)
    pinecone_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    pinecone_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    pinecone_host: Mapped[str] = mapped_column(String(512), default="")
    pinecone_namespace: Mapped[str] = mapped_column(String(255), default="")
    pinecone_dimension: Mapped[int] = mapped_column(Integer, default=1536)
    iac_scan_paths: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    iac_checks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    data_movement_policy: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GenaiEvidenceBundle(Base):
    __tablename__ = "genai_evidence_bundles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    actor: Mapped[str] = mapped_column(String(255), default="")
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class PolicyExemption(Base):
    __tablename__ = "policy_exemptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    ticket_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    allowed_destinations: Mapped[list] = mapped_column(JSONB, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ReportDefinition(Base):
    __tablename__ = "report_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    slug: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    format: Mapped[str] = mapped_column(String(20), default="CSV")
    query: Mapped[dict] = mapped_column(JSONB, default=dict)
    schedule_frequency: Mapped[str] = mapped_column(String(20), default="on_demand")
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_time: Mapped[str] = mapped_column(String(5), default="09:00")
    schedule_day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_recipients: Mapped[list] = mapped_column(JSONB, default=list)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation_status: Mapped[str] = mapped_column(String(20), default="idle")
    last_run_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RoutingGroup(Base):
    __tablename__ = "routing_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    strategy: Mapped[str] = mapped_column(String(50), default="weighted")
    members: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enforce_mode: Mapped[str] = mapped_column(String(32), default="warn")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["PromptVersion"]] = relationship("PromptVersion", back_populates="template", cascade="all, delete-orphan")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompt_templates.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list] = mapped_column(JSONB, default=list)
    created_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    template: Mapped[PromptTemplate] = relationship("PromptTemplate", back_populates="versions")


class CustomIntent(Base):
    __tablename__ = "custom_intents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(String(32), default="block")
    keywords: Mapped[list] = mapped_column(JSONB, default=list)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.8)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("custom_intents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    intent_type: Mapped[str] = mapped_column(String(32), default="intent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


