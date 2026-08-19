"""Page-aware help context catalog for the AI help chat."""

from __future__ import annotations

PAGE_CONTEXTS: list[dict] = [
    {
        "prefix": "/settings/ai-assist",
        "page_key": "settings-ai-assist",
        "page_label": "AI Assist settings",
        "guide_slug": "ai-assist",
        "summary": "Configure platform AI Assist provider credentials and tenant default LLM upstream keys.",
        "help_ids": ["settings-group-nav", "header-help"],
    },
    {
        "prefix": "/settings/integrations",
        "page_key": "settings-integrations",
        "page_label": "Integrations",
        "guide_slug": "settings",
        "summary": "Connect Vault secrets, Pinecone vector store, and alert webhooks for your tenant.",
        "help_ids": ["settings-group-nav", "header-help"],
    },
    {
        "prefix": "/settings/prompts",
        "page_key": "settings-prompts",
        "page_label": "Prompt Templates",
        "guide_slug": "settings",
        "summary": "Centrally governed system prompts with {{var}} injection and strict/warn enforce modes at gateway ingress.",
        "help_ids": [
            "settings-group-nav",
            "prompt-template-list",
            "prompt-create-button",
            "header-help",
        ],
    },
    {
        "prefix": "/settings",
        "page_key": "settings",
        "page_label": "Settings",
        "guide_slug": "settings",
        "summary": "Tenant configuration grouped into workspace, AI & integrations, and access & identity.",
        "help_ids": ["settings-group-nav", "nav-sidebar", "header-help"],
    },
    {
        "prefix": "/policy-studio",
        "page_key": "policy-studio",
        "page_label": "Policy Studio",
        "guide_slug": "policy-studio",
        "summary": "Author gateway policies, custom intents, folders, and test rules before production enforcement.",
        "help_ids": ["nav-sidebar", "header-date-range", "header-help"],
    },
    {
        "prefix": "/monitoring",
        "page_key": "monitoring",
        "page_label": "Monitoring",
        "guide_slug": "monitoring",
        "summary": "Gateway KPIs, security analytics, and distributed traces across tabs.",
        "help_ids": ["nav-sidebar", "header-date-range", "header-help"],
    },
    {
        "prefix": "/compliance",
        "page_key": "compliance",
        "page_label": "Compliance",
        "guide_slug": "compliance",
        "summary": "Governed RAG, evidence bundles, DLP labels, and break-glass exemptions.",
        "help_ids": ["nav-sidebar", "header-help"],
    },
    {
        "prefix": "/ai-gateway",
        "page_key": "ai-gateway",
        "page_label": "AI Gateway",
        "guide_slug": "ai-gateway",
        "summary": "Live gateway traffic, violations, and enforcement outcomes.",
        "help_ids": ["nav-sidebar", "header-date-range", "header-help"],
    },
    {
        "prefix": "/llm-router",
        "page_key": "llm-router",
        "page_label": "LLM Router",
        "guide_slug": "llm-router",
        "summary": "Provider routing, failover groups, and client key assignment.",
        "help_ids": ["nav-sidebar", "header-help"],
    },
    {
        "prefix": "/audit-explorer",
        "page_key": "audit-explorer",
        "page_label": "Audit Explorer",
        "guide_slug": "audit-explorer",
        "summary": "Search tamper-evident audit events across gateway and governance actions.",
        "help_ids": ["nav-sidebar", "header-date-range", "header-help"],
    },
    {
        "prefix": "/mcp-governance",
        "page_key": "mcp-governance",
        "page_label": "MCP Governance",
        "guide_slug": "mcp-governance",
        "summary": "Register MCP servers, tool RBAC, and REST-to-MCP conversion.",
        "help_ids": ["nav-sidebar", "header-help"],
    },
    {
        "prefix": "/reports",
        "page_key": "reports",
        "page_label": "Reports",
        "guide_slug": "reports",
        "summary": "Executive period summaries, report catalog exports, and scheduled delivery.",
        "help_ids": ["nav-sidebar", "header-date-range", "header-help"],
    },
    {
        "prefix": "/data-protection",
        "page_key": "data-protection",
        "page_label": "Data Protection",
        "guide_slug": "compliance",
        "summary": "Regional data residency, PII handling, and DLP policy outcomes.",
        "help_ids": ["nav-sidebar", "header-help"],
    },
    {
        "prefix": "/settings/api-keys",
        "page_key": "settings-api-keys",
        "page_label": "Client API keys",
        "guide_slug": "client-api-keys",
        "summary": "Ingress keys, per-key limits, token saving, and policy bundle assignment.",
        "help_ids": ["settings-group-nav", "header-help"],
    },
    {
        "prefix": "/help",
        "page_key": "help",
        "page_label": "Help & resources",
        "guide_slug": None,
        "summary": "Onboarding steps, product guide articles, and trust policies.",
        "help_ids": ["header-help"],
    },
    {
        "prefix": "/",
        "page_key": "dashboard",
        "page_label": "Dashboard",
        "guide_slug": "dashboard",
        "summary": "Operational overview of gateway health, threats, and compliance posture.",
        "help_ids": ["nav-sidebar", "header-date-range", "header-help", "header-notifications"],
    },
]

HELP_TARGET_LABELS: dict[str, str] = {
    "nav-sidebar": "Main navigation sidebar",
    "header-date-range": "Date range picker",
    "header-help": "Help menu",
    "header-notifications": "Notifications",
    "header-theme": "Theme toggle",
    "header-profile": "Profile menu",
    "settings-group-nav": "Settings section tabs",
    "prompt-template-list": "Prompt templates table",
    "prompt-create-button": "Create template button",
}

GUIDE_ARTICLE_SNIPPETS: dict[str, str] = {
    "policy-studio": "Policy Studio: expression conditions, custom intents, policy tester, bundle assignment.",
    "ai-gateway": "AI Gateway: client API keys, policy bundles, prompt templates, rate limits.",
    "llm-router": "LLM Router: providers, routing rules, groups, client protocol binding.",
    "mcp-governance": "MCP Governance: server registry, tool RBAC, REST-to-MCP wizard.",
    "compliance": "Compliance: governed RAG, evidence bundles, DLP, break-glass exemptions.",
    "monitoring": "Monitoring: overview KPIs, security tab, traces tab.",
    "audit-explorer": "Audit Explorer: filter by actor, action, risk; export for compliance.",
    "settings": "Settings: integrations, gateway limits, identity, RBAC, prompt templates.",
    "ai-assist": "AI Assist: platform helper LLM credentials; enables Policy Studio, Compliance, Dashboard, and help chat.",
    "client-api-keys": "Client API keys: ingress secrets, per-key limits, bundle binding.",
    "dashboard": "Executive Dashboard: KPI cards, risk strip, operational detail tabs, AI metric insights.",
    "reports": "Reports: period summary KPIs, report catalog exports, scheduled delivery.",
}

GUIDE_SLUG_ALIASES: dict[str, str] = {
    "ai-assist-settings": "ai-assist",
    "settings-ai-assist": "ai-assist",
    "settings-integrations": "settings",
    "settings-prompts": "settings",
    "settings-api-keys": "client-api-keys",
    "prompt-templates": "settings",
    "api-keys": "client-api-keys",
    "monitoring-overview": "monitoring",
    "monitoring-security": "monitoring",
    "monitoring-traces": "monitoring",
    "monitoring-operations": "monitoring",
    "executive-dashboard": "dashboard",
    "gateway": "ai-gateway",
    "ai-gateway-connect": "ai-gateway",
    "compatibility-center": "ai-gateway",
    "mcp": "mcp-governance",
    "compliance-center": "compliance",
    "data-protection": "compliance",
    "audit": "audit-explorer",
    "executive-summary": "reports",
}

GUIDE_SLUG_PREFIX_RULES: list[tuple[str, str]] = [
    ("monitoring", "monitoring"),
    ("ai-gateway", "ai-gateway"),
    ("llm-router", "llm-router"),
    ("policy-studio", "policy-studio"),
    ("mcp", "mcp-governance"),
    ("compliance", "compliance"),
    ("data-protection", "compliance"),
    ("audit", "audit-explorer"),
    ("reports", "reports"),
    ("dashboard", "dashboard"),
    ("settings", "settings"),
    ("ai-assist", "ai-assist"),
    ("client-api", "client-api-keys"),
    ("api-key", "client-api-keys"),
    ("governance", "policy-studio"),
]

CANONICAL_GUIDE_SLUGS = frozenset(GUIDE_ARTICLE_SNIPPETS.keys())


def resolve_guide_slug(slug: str) -> str:
    normalized = slug.strip().lower()
    if normalized in GUIDE_SLUG_ALIASES:
        return GUIDE_SLUG_ALIASES[normalized]
    if normalized in CANONICAL_GUIDE_SLUGS:
        return normalized
    for prefix, target in GUIDE_SLUG_PREFIX_RULES:
        if normalized == prefix or normalized.startswith(f"{prefix}-"):
            return target
    return normalized


def normalize_guide_href(href: str) -> str:
    if not href.startswith("/help/guides/"):
        return href
    slug = href.removeprefix("/help/guides/").split("?")[0].split("#")[0].strip("/")
    if not slug:
        return "/help?tab=guides"
    resolved = resolve_guide_slug(slug)
    if resolved not in CANONICAL_GUIDE_SLUGS:
        return "/help?tab=guides"
    return f"/help/guides/{resolved}"


def resolve_page_context(pathname: str, search: str | None = None) -> dict:
    path = pathname or "/"
    tab = None
    if search:
        for part in search.lstrip("?").split("&"):
            if part.startswith("tab="):
                tab = part.split("=", 1)[1]
                break

    matched = PAGE_CONTEXTS[-1]
    for ctx in PAGE_CONTEXTS:
        prefix = ctx["prefix"]
        if prefix == "/" and path == "/":
            matched = ctx
            break
        if prefix != "/" and (path == prefix or path.startswith(f"{prefix}/")):
            matched = ctx
            break

    return {
        **matched,
        "pathname": path,
        "tab": tab,
    }
