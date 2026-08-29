"""Edge Gateway and Multi-Region Data Plane models."""

import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.tenant import Base


class EdgeGatewayNode(Base):
    """Enrolled Regional Edge Gateway Node in the distributed control plane mesh."""

    __tablename__ = "edge_gateway_nodes"
    __table_args__ = (
        UniqueConstraint("node_id", name="uq_edge_gateway_nodes_node_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    node_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    region = Column(String(64), nullable=False, default="us-east-1", index=True)
    cloud_provider = Column(String(64), nullable=False, default="aws")
    status = Column(String(32), nullable=False, default="active", index=True)
    ip_address = Column(String(64), nullable=True)
    hostname = Column(String(255), nullable=True)
    enrollment_token_hash = Column(String(255), nullable=False)
    bundle_version = Column(Integer, nullable=False, default=1)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    sync_latency_ms = Column(Float, nullable=False, default=1.2)
    requests_routed_24h = Column(Integer, nullable=False, default=0)
    cpu_percent = Column(Float, nullable=True, default=12.5)
    memory_percent = Column(Float, nullable=True, default=24.0)
    meta_info = Column(JSONB, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
