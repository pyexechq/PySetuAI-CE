from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.blog import BlogArticlePublicResponse
from app.services.blog_service import get_blog_article, list_blog_articles

router = APIRouter(prefix="/blog", tags=["blog"])


@router.get("", response_model=list[BlogArticlePublicResponse])
async def list_published_articles(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BlogArticlePublicResponse]:
    rows = await list_blog_articles(db, published_only=True)
    return [BlogArticlePublicResponse(**row) for row in rows]


@router.get("/{slug}", response_model=BlogArticlePublicResponse)
async def get_published_article(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BlogArticlePublicResponse:
    row = await get_blog_article(db, slug, published_only=True)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return BlogArticlePublicResponse(**row)
