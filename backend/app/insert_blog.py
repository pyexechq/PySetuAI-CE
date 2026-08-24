import asyncio
from datetime import datetime, timezone
import sys

sys.path.append("/app")
from app.db.session import async_session_factory
from app.models.blog import BlogArticle
from sqlalchemy import select

async def main():
    slug = "self-service-developer-portal-mcp-governance"
    async with async_session_factory() as session:
        result = await session.execute(select(BlogArticle).where(BlogArticle.slug == slug))
        existing = result.scalar_one_or_none()
        
        content = [
            {
                "heading": "The Friction in Enterprise Agent Tooling",
                "body": [
                    "As organizations scale AI agent adoption, developers constantly need access to specialized tools—ranging from internal SQL databases and GitHub repositories to Salesforce CRM and ERP systems. Traditionally, connecting an agent to enterprise data required weeks of manual ticket approvals, ad-hoc API token sharing, and unmonitored local configurations.",
                    "Without unified governance, security teams are left blind to which developers and agents are executing operations against mission-critical infrastructure. PySetu AI eliminates this tension with the Self-Service Developer Portal."
                ],
            },
            {
                "heading": "Self-Service Discovery and Granular Operation Requests",
                "body": [
                    "Through the unified Developer Portal (/developer-portal), developers browse an interactive catalogue of published, security-vetted MCP servers. Rather than requesting blanket access, developers can select specific operations (e.g., read-only file queries vs. destructive writes) and submit them with a clear business justification.",
                    "The access request cart aggregates multiple tool permissions into a single approval flow routed directly to the tenant's Approval Center."
                ],
            },
            {
                "heading": "Zero-Touch Key Provisioning & Client Config Delivery",
                "body": [
                    "Upon approval, PySetu's backend automatically provisions an encrypted, rate-limited Client API key with attached DLP and OPA governance bundles. Developers instantly receive pre-formatted configuration blocks for Claude Desktop, Cursor, and IDE extensions—enabling immediate productivity without manual key handling.",
                    "Developers can also validate their prompts and tool invocations against live policies in the integrated Agent Playground."
                ],
            },
            {
                "heading": "Full-Stack RBAC, Grant Revocation, and SaaS Entitlements",
                "body": [
                    "For security administrators, the MCP Governance Access & RBAC dashboard provides continuous visibility into every active grant, authorized developer, and approved operation. Administrators can instantly revoke access with a single click.",
                    "Furthermore, multi-tenant SaaS platform operators retain top-level control, enabling or disabling the Developer Portal module on a per-tenant basis from Platform Ops."
                ],
            },
        ]
        
        if existing:
            existing.title = "Self-Service Developer Portal: Bridging AI Developers, Governed MCP Tools, and Enterprise RBAC"
            existing.excerpt = "How PySetu AI empowers agent builders with a self-service MCP catalogue, automated key provisioning, live RBAC grant revocation, and multi-tenant SaaS operator entitlements."
            existing.content = content
            existing.published = True
            existing.tags = ["Developer Portal", "MCP Governance", "RBAC", "AI Gateway"]
            existing.feature = "Developer Portal & MCP Governance"
            print("Blog article updated!")
        else:
            article = BlogArticle(
                slug=slug,
                title="Self-Service Developer Portal: Bridging AI Developers, Governed MCP Tools, and Enterprise RBAC",
                excerpt="How PySetu AI empowers agent builders with a self-service MCP catalogue, automated key provisioning, live RBAC grant revocation, and multi-tenant SaaS operator entitlements.",
                category="Feature",
                feature="Developer Portal & MCP Governance",
                date=datetime.now(timezone.utc),
                read_time="6 min read",
                author="PySetu AI Engineering",
                tags=["Developer Portal", "MCP Governance", "RBAC", "AI Gateway"],
                published=True,
                content=content,
            )
            session.add(article)
            print("Blog article created!")
            
        await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
