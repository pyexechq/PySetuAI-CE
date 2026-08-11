import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db import async_session_factory
from app.models.governance import AuditLog, ClientApiKey, LLMProvider, MCPServer, Policy, PolicyBundle, RoutingRule
from app.models.tenant import Tenant
from app.models.uag import UagModelMapping, UagTranslationPolicy
from app.services.client_api_key_service import hash_client_key

POLICY_RULES = [
    {
        "id": "r1",
        "name": "Detect SSN patterns",
        "condition": "content.matches(/\\d{3}-\\d{2}-\\d{4}/)",
        "action": "Redact",
        "severity": "high",
        "enabled": True,
    },
    {
        "id": "r2",
        "name": "Block system prompt override",
        "condition": "content.matches(/ignore\\s+(all\\s+)?previous\\s+instructions/i)",
        "action": "Block",
        "severity": "critical",
        "enabled": True,
    },
    {
        "id": "r3",
        "name": "EU data residency check",
        "condition": "region != 'EU' && has_pii",
        "action": "Block",
        "severity": "high",
        "enabled": True,
    },
    {
        "id": "r4",
        "name": "Log sensitive tool calls",
        "condition": "mcp.tool in sensitive_tools",
        "action": "Alert",
        "severity": "medium",
        "enabled": True,
    },
    {
        "id": "r5",
        "name": "Toxic content threshold",
        "condition": "toxicity_score > 0.85",
        "action": "Block",
        "severity": "medium",
        "enabled": False,
    },
]

PII_EU_RULES = [
    {
        "id": "eu-r1",
        "name": "Detect EU personal ID patterns",
        "condition": "content.matches(/\\b[A-Z]{2}\\d{6,12}\\b/)",
        "action": "Redact",
        "severity": "high",
        "enabled": True,
    },
    {
        "id": "eu-r2",
        "name": "EU residency gate",
        "condition": "region != 'EU' && has_pii",
        "action": "Block",
        "severity": "high",
        "enabled": True,
    },
    {
        "id": "eu-r3",
        "name": "Log cross-border PII access",
        "condition": "has_pii && region != user_region",
        "action": "Alert",
        "severity": "medium",
        "enabled": True,
    },
]

PII_US_RULES = [
    {
        "id": "us-r1",
        "name": "Detect SSN patterns",
        "condition": "content.matches(/\\d{3}-\\d{2}-\\d{4}/)",
        "action": "Redact",
        "severity": "high",
        "enabled": True,
    },
    {
        "id": "us-r2",
        "name": "Detect US phone numbers",
        "condition": "content.matches(/\\b\\d{3}-\\d{3}-\\d{4}\\b/)",
        "action": "Redact",
        "severity": "medium",
        "enabled": True,
    },
]

DLP_CLASSIFICATION_RULES = [
    {
        "id": "dlp-r1",
        "name": "Classify EU personal data",
        "condition": "region == 'EU' && has_pii",
        "action": "Redact",
        "severity": "high",
        "enabled": True,
    },
    {
        "id": "dlp-r2",
        "name": "Classify US sensitive identifiers",
        "condition": "region == 'US' && has_pii",
        "action": "Redact",
        "severity": "high",
        "enabled": True,
    },
    {
        "id": "dlp-r3",
        "name": "Cross-border residency block",
        "condition": "region != user_region && has_pii",
        "action": "Block",
        "severity": "critical",
        "enabled": True,
    },
]

JAILBREAK_RULES = [
    {
        "id": "jb-r1",
        "name": "Block DAN jailbreak",
        "condition": "prompt.contains('you are now dan')",
        "action": "Block",
        "severity": "critical",
        "enabled": True,
    },
    {
        "id": "jb-r2",
        "name": "Block instruction override",
        "condition": "content.matches(/ignore\\s+(all\\s+)?previous\\s+instructions/i)",
        "action": "Block",
        "severity": "critical",
        "enabled": True,
    },
    {
        "id": "jb-r3",
        "name": "Block system prompt reveal",
        "condition": "content.matches(/(reveal|show|print|repeat|output|display)\\s+(me\\s+)?(your\\s+)?(system\\s+)?(prompt|instructions)/i)",
        "action": "Block",
        "severity": "critical",
        "enabled": True,
    },
    {
        "id": "jb-r4",
        "name": "Block unrestricted mode",
        "condition": "content.matches(/(developer|god|sudo|unrestricted|admin)\\s+mode/i)",
        "action": "Block",
        "severity": "high",
        "enabled": True,
    },
    {
        "id": "jb-r5",
        "name": "Block safety rule bypass",
        "condition": "content.matches(/(forget\\s+(all\\s+)?(your\\s+)?(rules|instructions|guidelines)|bypass\\s+(your\\s+)?(restrictions|rules|guardrails|filters))/i)",
        "action": "Block",
        "severity": "high",
        "enabled": True,
    },
]

POLICY_RULE_SETS: dict[str, list] = {
    "Prompt Injection Guard": POLICY_RULES,
    "PII Redaction — EU": PII_EU_RULES,
    "PII Redaction — US": PII_US_RULES,
    "Jailbreak Prevention": JAILBREAK_RULES,
    "DLP Classification": DLP_CLASSIFICATION_RULES,
}

POLICY_TREE = [
    ("Organization Policies", "folder", None, None),
    ("Data Protection", "folder", "Organization Policies", None),
    ("PII Redaction — EU", "policy", "Data Protection", "active"),
    ("PII Redaction — US", "policy", "Data Protection", "active"),
    ("DLP Classification", "policy", "Data Protection", "active"),
    ("Security Controls", "folder", "Organization Policies", None),
    ("Prompt Injection Guard", "policy", "Security Controls", "active"),
    ("Jailbreak Prevention", "policy", "Security Controls", "active"),
    ("Data Exfiltration Block", "policy", "Security Controls", "active"),
    ("MCP Governance", "folder", "Organization Policies", None),
    ("Tool Allowlist", "policy", "MCP Governance", "active"),
    ("Rate Limiting", "policy", "MCP Governance", "disabled"),
]

MCP_SERVERS = [
    ("HR Database MCP", "Human Resources", 99.2, 124, 128310, 92.0, 12.0, "healthy", 12),
    ("Finance Sync API", "Finance", 97.8, 210, 82310, 88.0, 28.0, "healthy", 8),
    ("Payroll System", "Finance", 94.1, 380, 58510, 75.0, 45.0, "degraded", 6),
    ("Jira Integration", "Productivity", 99.6, 95, 45200, 95.0, 8.0, "healthy", 15),
    ("Salesforce CRM", "Sales", 98.3, 156, 67800, 90.0, 15.0, "healthy", 22),
    ("Legacy ERP Bridge", "Finance", 82.4, 890, 12400, 40.0, 78.0, "offline", 4),
]

AUDIT_LOGS = [
    ("support-agent@v1", "LLM Request", "GPT-4o /chat", "allowed", "low", "Customer query processed"),
    ("code-copilot@v2", "Policy Check", "Prompt Injection Guard", "blocked", "high", "Detected override attempt"),
    ("hr-bot@v1", "MCP Tool Call", "HR Database /query", "allowed", "low", "Employee lookup"),
    ("finance-bot@v1", "DLP Scan", "PII Redaction — EU", "review", "medium", "SSN pattern detected, redacted"),
    ("sales-agent@v3", "LLM Request", "Claude 3.5 /chat", "allowed", "low", "Proposal draft generated"),
    ("unknown-client", "Auth Attempt", "AI Gateway", "blocked", "high", "Invalid JWT token"),
    ("support-agent@v1", "MCP Tool Call", "Jira /create-ticket", "allowed", "low", "Ticket INC-4521 created"),
    (
        "code-copilot@v2",
        "Data Exfiltration",
        "Exfiltration Block",
        "blocked",
        "high",
        "Attempted base64 payload export",
    ),
]

LLM_PROVIDERS = [
    ("GPT-4o", "openai", 5670000, 45.0, 842, 99.1),
    ("Gemini 1.5 Pro", "gemini", 3780000, 30.0, 920, 98.5),
    ("Claude 3.5 Sonnet", "anthropic", 1890000, 15.0, 1100, 97.8),
    ("Llama 3.1 70B", "ollama", 1260000, 10.0, 680, 96.4),
]

ROUTING_RULES = [
    ("Code tasks → Claude", 1, "task.type == 'code_review'", "Claude 3.5 Sonnet", "active"),
    ("Low latency → Llama", 2, "sla.latency_ms < 500", "Llama 3.1 70B", "active"),
    ("Default → GPT-4o", 10, "default", "GPT-4o", "active"),
    ("Multimodal → Gemini", 3, "input.has_image", "Gemini 1.5 Pro", "draft"),
]

ACCESS_BUNDLES = [
    (
        "Standard Support",
        "Default bundle for customer-facing agents",
        True,
        ["Prompt Injection Guard", "PII Redaction — US"],
    ),
    (
        "Strict Security",
        "High-security bundle for code and internal tools",
        False,
        ["Prompt Injection Guard", "Jailbreak Prevention", "PII Redaction — EU"],
    ),
]

DEMO_CLIENT_KEYS = [
    ("Support Agent Key", "support-agent", "Standard Support", "hg_demo_acme_support2026"),
    ("Code Copilot Key", "code-copilot", "Strict Security", "hg_demo_acme_copilot2026"),
]


async def seed_governance_for_tenant(session, tenant_id: uuid.UUID) -> bool:
    """Load governance demo data for a tenant. Returns True if data was inserted."""
    mcp_count = await session.execute(select(MCPServer).where(MCPServer.tenant_id == tenant_id).limit(1))
    if mcp_count.scalar_one_or_none() is not None:
        return False

    policy_ids: dict[str, uuid.UUID] = {}
    for name, ptype, parent_name, status in POLICY_TREE:
        policy = Policy(
            tenant_id=tenant_id,
            name=name,
            policy_type=ptype,
            status=status or "active",
            parent_id=policy_ids.get(parent_name) if parent_name else None,
            rules=POLICY_RULE_SETS.get(name),
        )
        session.add(policy)
        await session.flush()
        policy_ids[name] = policy.id

    for row in MCP_SERVERS:
        session.add(
            MCPServer(
                tenant_id=tenant_id,
                name=row[0],
                category=row[1],
                success_rate=row[2],
                avg_latency_ms=row[3],
                total_calls=row[4],
                trust_score=row[5],
                risk_score=row[6],
                status=row[7],
                tools_count=row[8],
            )
        )

    base_time = datetime.now(UTC) - timedelta(hours=len(AUDIT_LOGS) + 2)
    for i, row in enumerate(AUDIT_LOGS):
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                timestamp=base_time.replace(minute=28 + i),
                actor=row[0],
                action=row[1],
                resource=row[2],
                status=row[3],
                risk=row[4],
                details=row[5],
            )
        )

    for row in LLM_PROVIDERS:
        session.add(
            LLMProvider(
                tenant_id=tenant_id,
                name=row[0],
                provider_type=row[1],
                total_requests=row[2],
                percentage=row[3],
                avg_latency_ms=row[4],
                success_rate=row[5],
            )
        )

    for row in ROUTING_RULES:
        session.add(
            RoutingRule(
                tenant_id=tenant_id,
                name=row[0],
                priority=row[1],
                condition=row[2],
                target_model=row[3],
                status=row[4],
            )
        )
    return True


async def seed_access_for_tenant(session, tenant_id: uuid.UUID) -> bool:
    """Load policy bundles and demo client keys for a tenant. Returns True if inserted."""
    bundle_check = await session.execute(select(PolicyBundle).where(PolicyBundle.tenant_id == tenant_id).limit(1))
    if bundle_check.scalar_one_or_none() is not None:
        return False

    policy_result = await session.execute(
        select(Policy).where(Policy.tenant_id == tenant_id, Policy.policy_type == "policy")
    )
    policy_by_name = {p.name: p.id for p in policy_result.scalars().all()}

    bundle_ids: dict[str, uuid.UUID] = {}
    for name, description, is_default, policy_names in ACCESS_BUNDLES:
        policy_ids = [str(policy_by_name[n]) for n in policy_names if n in policy_by_name]
        bundle = PolicyBundle(
            tenant_id=tenant_id,
            name=name,
            description=description,
            status="active",
            is_default=is_default,
            policy_ids=policy_ids,
        )
        session.add(bundle)
        await session.flush()
        bundle_ids[name] = bundle.id

    slug_suffix = str(tenant_id).split("-")[0]
    demo_keys = [
        ("Support Agent Key", "Standard Support", f"hg_demo_{slug_suffix}_support2026"),
        ("Code Copilot Key", "Strict Security", f"hg_demo_{slug_suffix}_copilot2026"),
    ]
    for key_name, bundle_name, raw_key in demo_keys:
        bundle_id = bundle_ids.get(bundle_name)
        session.add(
            ClientApiKey(
                tenant_id=tenant_id,
                name=key_name,
                description=f"Demo ingress key for {bundle_name} bundle",
                key_prefix=raw_key[:12],
                key_hash=hash_client_key(raw_key),
                bundle_id=bundle_id,
                is_active=True,
            )
        )
    return True


async def seed_uag_for_tenant(session, tenant_id: uuid.UUID) -> bool:
    existing = await session.execute(
        select(UagModelMapping).where(UagModelMapping.tenant_id == tenant_id).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return False

    for requested, actual, provider in (
        ("gpt-4o", "gemini-1.5-pro", "gemini"),
        ("gpt-4o-mini", "gemini-1.5-flash", "gemini"),
        ("gpt-5", "claude-sonnet-4", "claude"),
        ("gpt-4", "llama3:70b", "ollama"),
    ):
        session.add(
            UagModelMapping(
                tenant_id=tenant_id,
                requested_model=requested,
                actual_model=actual,
                target_provider=provider,
                emulate_protocol="openai",
                enabled=True,
            )
        )

    for name, conditions, actions, priority in (
        ("Finance to local LLM", {"department": "finance"}, {"route_to": "ollama"}, 10),
        ("EU data residency", {"country": "EU"}, {"route_to": "azure_openai"}, 20),
        ("Legacy app emulation", {"application": "legacy_app"}, {"emulate": "openai"}, 30),
    ):
        session.add(
            UagTranslationPolicy(
                tenant_id=tenant_id,
                name=name,
                conditions=conditions,
                actions=actions,
                priority=priority,
                enabled=True,
            )
        )
    return True


async def seed_uag_data() -> None:
    async with async_session_factory() as session:
        tenant_result = await session.execute(select(Tenant).where(Tenant.slug == "acme"))
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            return
        if await seed_uag_for_tenant(session, tenant.id):
            await session.commit()


async def seed_governance_data() -> None:
    async with async_session_factory() as session:
        tenant_result = await session.execute(select(Tenant).where(Tenant.slug == "acme"))
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            return

        if await seed_governance_for_tenant(session, tenant.id):
            await session.commit()


async def seed_access_data() -> None:
    """Seed policy bundles and demo client API keys when missing."""
    async with async_session_factory() as session:
        tenant_result = await session.execute(select(Tenant).where(Tenant.slug == "acme"))
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            return

        if await seed_access_for_tenant(session, tenant.id):
            await session.commit()
            print("Access seed: demo client API keys created for acme tenant.")


async def seed_all_governance() -> None:
    await seed_governance_data()
    await seed_access_data()


def main() -> None:
    asyncio.run(seed_all_governance())
    print("Governance seed data applied.")


if __name__ == "__main__":
    main()
