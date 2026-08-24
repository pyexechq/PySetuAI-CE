import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog import BlogArticle
from app.schemas.blog import BlogArticleCreateRequest, BlogArticleUpdateRequest


def _article_dict(article: BlogArticle) -> dict:
    return {
        "id": str(article.id),
        "slug": article.slug,
        "title": article.title,
        "excerpt": article.excerpt,
        "category": article.category,
        "feature": article.feature,
        "date": article.date,
        "read_time": article.read_time,
        "author": article.author,
        "tags": article.tags or [],
        "content": article.content or [],
        "image_url": article.image_url,
        "published": article.published,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }


async def list_blog_articles(db: AsyncSession, *, published_only: bool = False) -> list[dict]:
    stmt = select(BlogArticle).order_by(BlogArticle.date.desc())
    if published_only:
        stmt = stmt.where(BlogArticle.published.is_(True))
    result = await db.execute(stmt)
    return [_article_dict(a) for a in result.scalars().all()]


async def get_blog_article(db: AsyncSession, slug: str, *, published_only: bool = False) -> dict | None:
    stmt = select(BlogArticle).where(BlogArticle.slug == slug)
    if published_only:
        stmt = stmt.where(BlogArticle.published.is_(True))
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()
    return _article_dict(article) if article else None


async def get_blog_article_by_id(db: AsyncSession, article_id: uuid.UUID) -> BlogArticle | None:
    result = await db.execute(select(BlogArticle).where(BlogArticle.id == article_id))
    return result.scalar_one_or_none()


async def create_blog_article(db: AsyncSession, payload: BlogArticleCreateRequest) -> dict:
    existing = await db.execute(select(BlogArticle).where(BlogArticle.slug == payload.slug))
    if existing.scalar_one_or_none() is not None:
        raise ValueError(f"An article with slug '{payload.slug}' already exists")

    article = BlogArticle(
        slug=payload.slug,
        title=payload.title,
        excerpt=payload.excerpt,
        category=payload.category,
        feature=payload.feature,
        date=payload.date,
        read_time=payload.read_time,
        author=payload.author,
        tags=payload.tags,
        content=[s.model_dump() for s in payload.content],
        published=payload.published,
    )
    db.add(article)
    await db.flush()
    return _article_dict(article)


async def update_blog_article(
    db: AsyncSession, article: BlogArticle, payload: BlogArticleUpdateRequest
) -> dict:
    data = payload.model_dump(exclude_unset=True)
    if "content" in data and data["content"] is not None:
        data["content"] = [s.model_dump() for s in data["content"]]
    for field, value in data.items():
        setattr(article, field, value)
    article.updated_at = datetime.now()
    await db.flush()
    return _article_dict(article)


async def set_blog_article_published(db: AsyncSession, article: BlogArticle, published: bool) -> dict:
    article.published = published
    article.updated_at = datetime.now()
    await db.flush()
    return _article_dict(article)


async def delete_blog_article(db: AsyncSession, article: BlogArticle) -> None:
    await db.delete(article)
    await db.flush()
