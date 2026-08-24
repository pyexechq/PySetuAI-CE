import asyncio
from datetime import datetime
import sys

sys.path.append("/app")
from app.db.session import async_session_factory
from app.models.blog import BlogArticle
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(BlogArticle).where(BlogArticle.slug == "endpoint-agents-browser-extensions"))
        if result.scalar_one_or_none():
            print("Blog already exists")
            return

        article = BlogArticle(
            slug="endpoint-agents-browser-extensions",
            title="Securing the Edge: Endpoint Agents & Browser Extensions",
            excerpt="Extend PySetu's security boundary directly to the developer's workstation or browser with native macOS, Windows, Linux agents, and browser extensions.",
            category="Feature",
            feature="Endpoint Enforcement",
            date=datetime.utcnow(),
            read_time="3 min read",
            author="PySetu AI Team",
            tags=["Security", "Endpoint", "Agents", "Browser Extensions"],
            image_url="https://images.unsplash.com/photo-1555949963-aa79dcee981c?auto=format&fit=crop&q=80&w=1000",
            published=True,
            content=[
                {
                    "type": "paragraph",
                    "content": "Today, we are thrilled to announce a major expansion of the PySetu AI Agentic Control Plane: Endpoint Agents and Browser Extensions."
                }
            ]
        )
        session.add(article)
        await session.commit()
        print("Blog article successfully created!")

if __name__ == "__main__":
    asyncio.run(main())
