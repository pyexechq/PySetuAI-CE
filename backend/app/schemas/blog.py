from datetime import datetime

from pydantic import BaseModel, Field


class BlogContentSection(BaseModel):
    heading: str
    body: list[str]


class BlogArticleBase(BaseModel):
    slug: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    excerpt: str = Field(default="", max_length=2000)
    category: str = Field(default="Feature", max_length=32)
    feature: str = Field(default="", max_length=255)
    date: datetime
    read_time: str = Field(default="5 min read", max_length=32)
    author: str = Field(default="PySetu AI Team", max_length=255)
    tags: list[str] = Field(default_factory=list)
    content: list[BlogContentSection] = Field(default_factory=list)
    image_url: str | None = Field(default=None, max_length=2048)


class BlogArticleCreateRequest(BlogArticleBase):
    published: bool = False


class BlogArticleUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    excerpt: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=32)
    feature: str | None = Field(default=None, max_length=255)
    date: datetime | None = None
    read_time: str | None = Field(default=None, max_length=32)
    author: str | None = Field(default=None, max_length=255)
    tags: list[str] | None = None
    content: list[BlogContentSection] | None = None
    image_url: str | None = Field(default=None, max_length=2048)
    published: bool | None = None


class BlogArticleResponse(BlogArticleBase):
    id: str
    published: bool
    created_at: datetime
    updated_at: datetime


class BlogArticlePublicResponse(BlogArticleBase):
    id: str
    published: bool
