import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.tenant import Base


class BlogArticle(Base):
    __tablename__ = "blog_articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="Feature", nullable=False)
    feature: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read_time: Mapped[str] = mapped_column(String(32), default="5 min read", nullable=False)
    author: Mapped[str] = mapped_column(String(255), default="PySetu AI Team", nullable=False)
    tags: Mapped[list | None] = mapped_column(JSONB, default=list, nullable=True)
    content: Mapped[list | None] = mapped_column(JSONB, default=list, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
