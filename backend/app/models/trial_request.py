import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.tenant import Base


class TrialRequest(Base):
    __tablename__ = "trial_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(128), nullable=False)
    work_email = Column(String(255), nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    team_size = Column(String(64), nullable=True)
    use_case = Column(String(128), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending, contacted, approved, provisioned
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
