import type { LucideIcon } from "lucide-react";
import {
  BookOpen,
  Cookie,
  FileCheck,
  FileText,
  KeyRound,
  Radar,
  Route,
  Server,
  Settings,
  Shield,
  Sparkles,
  Workflow,
} from "lucide-react";

export type HelpTab = "getting-started" | "guides" | "policies";

export type HelpGuideIconId =
  | "workflow"
  | "shield"
  | "route"
  | "server"
  | "file-check"
  | "radar"
  | "file-text"
  | "settings"
  | "key-round"
  | "sparkles";

export const HELP_GUIDE_ICONS: Record<HelpGuideIconId, LucideIcon> = {
  workflow: Workflow,
  shield: Shield,
  route: Route,
  server: Server,
  "file-check": FileCheck,
  radar: Radar,
  "file-text": FileText,
  settings: Settings,
  "key-round": KeyRound,
  sparkles: Sparkles,
};

export const HELP_TABS: { id: HelpTab; label: string }[] = [
  { id: "getting-started", label: "Getting started" },
  { id: "guides", label: "Product guides" },
  { id: "policies", label: "Policies & trust" },
];

export interface HelpGuideSummary {
  slug: string;
  label: string;
  description: string;
  icon: HelpGuideIconId;
  readMinutes: number;
}

export interface HelpGuideArticle extends HelpGuideSummary {
  summary: string;
  featureHref: string;
  sections: { title: string; paragraphs: string[] }[];
  tips: string[];
}

export const HELP_GETTING_STARTED = [
  {
    step: 1,
    title: "Connect integrations",
    description:
      "Vault is enabled by default for tenant API keys. Configure Pinecone vector store and alert webhooks under Settings → Integrations.",
    articleSlug: "settings",
  },
  {
    step: 2,
    title: "Define gateway access",
    description:
      "Create a policy bundle, issue a client API key, and set rate or token limits for each application.",
    articleSlug: "client-api-keys",
  },
  {
    step: 3,
    title: "Author governance rules",
    description:
      "Use Policy Studio to block jailbreaks, redact PII, and test conditions before enforcing them in production.",
    articleSlug: "policy-studio",
  },
  {
    step: 4,
    title: "Monitor and audit",
    description:
      "Review gateway health in Monitoring and investigate decisions in Audit Explorer.",
    articleSlug: "monitoring",
  },
] as const;

export const HELP_GUIDE_ARTICLES: HelpGuideArticle[] = [
  {
    slug: "policy-studio",
    label: "Policy Studio",
    description: "Author rules, custom intents, condition syntax, and policy testing.",
    icon: "workflow",
    readMinutes: 6,
    featureHref: "/policy-studio",
    summary:
      "Policy Studio is where security and platform teams define what the AI gateway allows, redacts, or blocks before traffic reaches an LLM.",
    sections: [
      {
        title: "What you can do here",
        paragraphs: [
          "Create folder hierarchies and individual policies with expression-style conditions such as prompt substring matches, regex patterns, and PII gates.",
          "Use custom intents for keyword or semantic guardrails, and open the policy tester to validate outcomes before enabling rules in production.",
        ],
      },
      {
        title: "Condition syntax basics",
        paragraphs: [
          "Conditions run at gateway ingress against prompt and content fields. Common patterns include prompt.contains('phrase'), content.matches(/regex/i), has_pii, and region != 'EU'.",
          "Click the help icon inside Add/Edit Rule for copy-paste examples. Start with warn mode on new rules, then move to block once validated.",
        ],
      },
      {
        title: "Recommended workflow",
        paragraphs: [
          "Draft policies in a sandbox folder, test with representative prompts, attach policies to a bundle, and assign that bundle to a client API key in Settings.",
        ],
      },
    ],
    tips: [
      "Use Block for jailbreak and exfiltration patterns; use Redact for SSN and phone formats.",
      "Pair Policy Studio rules with prompt templates for defense in depth.",
    ],
  },
  {
    slug: "ai-gateway",
    label: "AI Gateway",
    description: "Inspect live gateway traffic, violations, and enforcement outcomes.",
    icon: "shield",
    readMinutes: 5,
    featureHref: "/ai-gateway",
    summary:
      "The AI Gateway is the enforcement edge for LLM requests. It applies policies, injects managed prompts, and records decisions for audit.",
    sections: [
      {
        title: "How requests flow",
        paragraphs: [
          "Applications call the gateway with a client API key. PySetu evaluates the key's policy bundle, optional prompt template, rate limits, and OPA policies before forwarding to the configured LLM route.",
          "Blocked or redacted requests never leave your tenant boundary with ungoverned content.",
        ],
      },
      {
        title: "What to monitor",
        paragraphs: [
          "Watch violation counts, top blocked conditions, and latency percentiles. Spikes often indicate a misconfigured bundle, an overly broad regex, or an application sending unexpected payloads.",
        ],
      },
      {
        title: "Testing safely",
        paragraphs: [
          "Use the gateway tester and Governance Sandbox with the same client key your app will use. Confirm both allow and deny paths before promoting changes.",
        ],
      },
    ],
    tips: [
      "Assign one bundle per application persona (support bot vs. internal copilot).",
      "Enable token saving on keys that fan out to expensive models.",
    ],
  },
  {
    slug: "llm-router",
    label: "LLM Router",
    description: "Configure provider routing, failover groups, and client key assignment.",
    icon: "route",
    readMinutes: 5,
    featureHref: "/llm-router",
    summary:
      "LLM Router directs governed traffic to the right model provider based on rules, budgets, and failover groups.",
    sections: [
      {
        title: "Core concepts",
        paragraphs: [
          "Providers represent upstream LLM endpoints (OpenAI-compatible, Gemini, Anthropic, Ollama). Routing rules match request metadata—model name, client key, tags—and select a target.",
          "Routing groups bundle models for failover when a provider is degraded or over budget.",
        ],
      },
      {
        title: "Client key binding",
        paragraphs: [
          "Ingress keys can inherit tenant defaults or override the client protocol (OpenAI chat, Gemini GenerateContent, Anthropic Messages). Match the protocol your SDK sends.",
        ],
      },
      {
        title: "Operations",
        paragraphs: [
          "Review provider health cards and rebalance schedules. Use Monitoring traces to confirm which route handled each request.",
        ],
      },
    ],
    tips: [
      "Put latency-sensitive workloads on a dedicated routing group with a fast fallback model.",
      "Document model aliases your apps send so conditions stay maintainable.",
    ],
  },
  {
    slug: "mcp-governance",
    label: "MCP Governance",
    description: "Register MCP servers, tool RBAC, and REST-to-MCP conversion.",
    icon: "server",
    readMinutes: 6,
    featureHref: "/mcp-governance",
    summary:
      "MCP Governance controls which tools agents can discover and invoke, with audit trails for every tool call.",
    sections: [
      {
        title: "Registering servers",
        paragraphs: [
          "Add MCP servers with connection details and scope them to your tenant. The REST-to-MCP wizard can wrap existing HTTP APIs as tools when you need quick coverage.",
        ],
      },
      {
        title: "Tool-level RBAC",
        paragraphs: [
          "Deny lists restrict roles or applications from calling sensitive tools (delete, export, admin). Enforcement happens before the tool executes.",
        ],
      },
      {
        title: "Audit and compliance",
        paragraphs: [
          "Tool invocations appear in Audit Explorer with actor, server, tool name, and allow/deny outcome—useful for SOC reviews and agent safety programs.",
        ],
      },
    ],
    tips: [
      "Hide destructive tools by default and expose them only to break-glass roles.",
      "Name tools clearly so policy conditions can reference mcp.tool safely.",
    ],
  },
  {
    slug: "compliance",
    label: "Compliance",
    description: "Governed RAG ingest, evidence bundles, DLP labels, and break-glass exemptions.",
    icon: "file-check",
    readMinutes: 7,
    featureHref: "/compliance",
    summary:
      "Compliance brings GenAI DLP to retrieval workflows: classify content, enforce data-movement policy, and retain evidence for regulators.",
    sections: [
      {
        title: "Governed RAG",
        paragraphs: [
          "Ingest and query paths evaluate sensitivity labels (PII, PCI, PHI) and OPA data-movement rules before embeddings or vector upserts occur.",
          "Configure Pinecone under Settings → Integrations when using the managed vector adapter.",
        ],
      },
      {
        title: "Evidence bundles",
        paragraphs: [
          "Each governed action can emit an evidence bundle capturing policy version, labels applied, hops traversed, and allow/block rationale.",
        ],
      },
      {
        title: "Break-glass exemptions",
        paragraphs: [
          "Time-bound exemptions let approved operators bypass specific policies during incidents. All exemption use is audited—treat them like production credentials.",
        ],
      },
    ],
    tips: [
      "Run dry-run evaluate calls before bulk ingest jobs.",
      "Pair DLP labels with region residency policies for cross-border datasets.",
    ],
  },
  {
    slug: "monitoring",
    label: "Monitoring",
    description: "Gateway KPIs, security analytics, and distributed traces.",
    icon: "radar",
    readMinutes: 4,
    featureHref: "/monitoring",
    summary:
      "Monitoring gives operators a live view of gateway health, security signals, and request traces.",
    sections: [
      {
        title: "Overview tab",
        paragraphs: [
          "Track request volume, error rates, token usage, and policy outcomes. Use the date range picker in the header to compare weeks or incident windows.",
        ],
      },
      {
        title: "Security tab",
        paragraphs: [
          "Review blocked jailbreak attempts, redaction counts, and top violating policies. Security and auditor roles see this tab by default.",
        ],
      },
      {
        title: "Traces tab",
        paragraphs: [
          "Drill into individual requests to see routing decisions, policy evaluations, and latency breakdowns—ideal when debugging false positives.",
        ],
      },
    ],
    tips: [
      "Set alert webhooks in Settings → Integrations for sustained block-rate spikes.",
      "Correlate Monitoring spikes with Audit Explorer for root-cause narratives.",
    ],
  },
  {
    slug: "audit-explorer",
    label: "Audit Explorer",
    description: "Search tamper-evident audit events across gateway and governance actions.",
    icon: "file-text",
    readMinutes: 4,
    featureHref: "/audit-explorer",
    summary:
      "Audit Explorer is the system of record for who did what, when, and whether governance allowed it.",
    sections: [
      {
        title: "Searching events",
        paragraphs: [
          "Filter by actor, action, resource, risk level, and time range. Export result sets for compliance packets or incident timelines.",
        ],
      },
      {
        title: "Event types",
        paragraphs: [
          "You'll see gateway ingress, policy changes, MCP tool calls, RAG ingest, exemption grants, and administrative settings updates.",
        ],
      },
      {
        title: "Investigation workflow",
        paragraphs: [
          "Start from a Monitoring anomaly, locate the matching audit row, then open the related policy or client key to remediate.",
        ],
      },
    ],
    tips: [
      "Auditors typically work from high-risk filters first, then narrow by application key.",
      "Retention follows your tenant request log policy—plan exports before purge windows.",
    ],
  },
  {
    slug: "settings",
    label: "Settings",
    description: "Organization profile, integrations, gateway limits, identity, and RBAC.",
    icon: "settings",
    readMinutes: 5,
    featureHref: "/settings",
    summary:
      "Settings is organized into workspace, AI & integrations, and access & identity groups so admins can find configuration quickly.",
    sections: [
      {
        title: "Workspace",
        paragraphs: [
          "Organization covers tenant branding and module visibility. Appearance controls theme preferences for your user session.",
        ],
      },
      {
        title: "AI & integrations",
        paragraphs: [
          "Vault is enabled by default for tenant API keys. Configure Pinecone and alert webhooks; set AI Assist defaults; manage gateway rate limits, token saving default, and token budgets; and edit prompt templates with {{var}} injection.",
        ],
      },
      {
        title: "Access & identity",
        paragraphs: [
          "Policy bundles group ingress policies. Client API keys attach bundles and limits. Identity covers SSO domains and OIDC providers. Users & RBAC manages roles.",
        ],
      },
    ],
    tips: [
      "Change gateway limits in one save action on the Gateway limits page.",
      "Use strict enforce mode on prompt templates for regulated workloads.",
    ],
  },
  {
    slug: "ai-assist",
    label: "AI Assist settings",
    description: "Platform AI Assist provider keys and tenant default LLM configuration.",
    icon: "sparkles",
    readMinutes: 5,
    featureHref: "/settings/ai-assist",
    summary:
      "AI Assist powers in-product helpers (Policy Studio, Compliance, Dashboard insights, and the floating help chat). Configure the provider here; tenant LLM defaults are on the second tab.",
    sections: [
      {
        title: "Platform AI Assist tab",
        paragraphs: [
          "Enable AI Assist and choose a provider (OpenAI, Gemini, Groq, or local Ollama/vLLM in air-gap mode). Add an API key or base URL, then pick a model.",
          "When credentials are missing, helpers fall back to deterministic guidance instead of live LLM responses.",
        ],
      },
      {
        title: "Tenant LLM defaults tab",
        paragraphs: [
          "Set the default upstream LLM provider and API keys used by the gateway for tenant traffic—separate from AI Assist credentials used inside the product UI.",
          "Gateway ingress keys can still override protocol and routing per application.",
        ],
      },
      {
        title: "What AI Assist enables",
        paragraphs: [
          "Policy Studio rule suggestions, Compliance remediation plans, Dashboard metric insights, and the context-aware help chat with page highlighting.",
        ],
      },
    ],
    tips: [
      "Use gateway fallback only for demos—dedicated AI Assist keys are easier to rotate.",
      "In air-gap deployments, point Ollama or vLLM at your internal inference endpoint.",
    ],
  },
  {
    slug: "client-api-keys",
    label: "Client API keys",
    description: "Ingress keys, per-key limits, token saving, and bundle assignment.",
    icon: "key-round",
    readMinutes: 5,
    featureHref: "/settings/api-keys",
    summary:
      "Client API keys are how applications authenticate to the gateway. Each key inherits governance from its policy bundle and optional per-key limits.",
    sections: [
      {
        title: "Creating a key",
        paragraphs: [
          "Choose a descriptive name, select a policy bundle, and pick the client protocol your SDK uses. Copy the secret immediately—it is shown only once.",
        ],
      },
      {
        title: "Limits and token saving",
        paragraphs: [
          "Override tenant RPM/TPM caps per application. Token saving can inherit the Gateway limits default or be set per key to reduce cost on repetitive prompts.",
        ],
      },
      {
        title: "Rotation",
        paragraphs: [
          "Issue a new key, update the application config, verify traffic in Monitoring, then revoke the old key. Audit Explorer records key lifecycle events.",
        ],
      },
    ],
    tips: [
      "One key per application environment (dev/stage/prod).",
      "Never embed keys in mobile clients—proxy through your backend.",
    ],
  },
  {
    slug: "dashboard",
    label: "Executive Dashboard",
    description: "KPI cards, operational detail tabs, and AI metric insights.",
    icon: "radar",
    readMinutes: 4,
    featureHref: "/",
    summary:
      "The Executive Dashboard is your at-a-glance view of gateway traffic, compliance posture, risk metrics, and operational detail across governance, usage, cost, and MCP activity.",
    sections: [
      {
        title: "At a glance KPIs",
        paragraphs: [
          "Hero cards show total AI requests, success rate, compliance score, and blocked requests for the selected date range. Hover a card and click the sparkle icon for AI-generated summaries and recommended actions.",
        ],
      },
      {
        title: "Risk & spend strip",
        paragraphs: [
          "Secondary metrics cover PII redactions, policy violations, MCP violations, and LLM spend. Use the header date range picker to compare incident windows.",
        ],
      },
      {
        title: "Operational detail tabs",
        paragraphs: [
          "Switch between Governance (top policies and agents), LLM usage, Cost & savings, and MCP activity without scrolling through everything at once.",
        ],
      },
    ],
    tips: [
      "Use quick-link pills to jump to Monitoring, Compliance, or Compatibility when a KPI needs deeper investigation.",
      "Correlate dashboard spikes with Audit Explorer for root-cause timelines.",
    ],
  },
  {
    slug: "reports",
    label: "Reports",
    description: "Executive summaries, report catalog, and scheduled exports.",
    icon: "file-text",
    readMinutes: 4,
    featureHref: "/reports",
    summary:
      "Reports provides period summaries, downloadable exports, and optional scheduled delivery for compliance and leadership review.",
    sections: [
      {
        title: "Period summary",
        paragraphs: [
          "KPI cards reflect the selected reporting period from the header date range. Sparkle icons on cards offer the same AI metric insights as the Executive Dashboard.",
        ],
      },
      {
        title: "Report catalog",
        paragraphs: [
          "Run or download point-in-time exports. Live analytics remain in Monitoring and Compliance—reports are for snapshots and auditor packets.",
        ],
      },
      {
        title: "Scheduler",
        paragraphs: [
          "Tenant admins can queue due scheduled reports and verify delivery via Mailhog in demo environments.",
        ],
      },
    ],
    tips: [
      "Export audit evidence before retention purge windows.",
      "Pair scheduled reports with alert webhooks in Settings → Integrations.",
    ],
  },
];

export const HELP_GUIDES: HelpGuideSummary[] = HELP_GUIDE_ARTICLES.map(
  ({ slug, label, description, icon, readMinutes }) => ({
    slug,
    label,
    description,
    icon,
    readMinutes,
  })
);

export const HELP_GUIDE_SLUG_ALIASES: Record<string, string> = {
  // Settings & AI Assist
  "ai-assist-settings": "ai-assist",
  "settings-ai-assist": "ai-assist",
  "platform-ai-assist": "ai-assist",
  "settings-integrations": "settings",
  "settings-prompts": "settings",
  "settings-identity": "settings",
  "settings-gateway": "settings",
  "settings-api-keys": "client-api-keys",
  "prompt-templates": "settings",
  "integrations": "settings",
  // Client keys
  "api-keys": "client-api-keys",
  "client-keys": "client-api-keys",
  "ingress-keys": "client-api-keys",
  // Monitoring (common AI-invented tab slugs)
  "monitoring-overview": "monitoring",
  "monitoring-security": "monitoring",
  "monitoring-traces": "monitoring",
  "monitoring-operations": "monitoring",
  "monitoring-sla": "monitoring",
  "executive-dashboard": "dashboard",
  // Gateway & router
  gateway: "ai-gateway",
  "ai-gateway-connect": "ai-gateway",
  "ai-gateway-test": "ai-gateway",
  "ai-gateway-compatibility": "ai-gateway",
  router: "llm-router",
  "llm-router-gateway": "llm-router",
  "compatibility-center": "ai-gateway",
  // Policy & governance
  "policy-studio-rules": "policy-studio",
  "custom-intents": "policy-studio",
  "governance-graph": "policy-studio",
  "governance-sandbox": "policy-studio",
  studio: "policy-studio",
  // MCP
  mcp: "mcp-governance",
  "mcp-servers": "mcp-governance",
  // Compliance & data
  "compliance-center": "compliance",
  "data-protection": "compliance",
  dlp: "compliance",
  "governed-rag": "compliance",
  // Audit & reports
  audit: "audit-explorer",
  "audit-log": "audit-explorer",
  "executive-summary": "reports",
  "period-summary": "reports",
};

const CANONICAL_HELP_GUIDE_SLUGS = new Set(HELP_GUIDE_ARTICLES.map((article) => article.slug));

const HELP_GUIDE_SLUG_PREFIX_RULES: [string, string][] = [
  ["monitoring", "monitoring"],
  ["ai-gateway", "ai-gateway"],
  ["llm-router", "llm-router"],
  ["policy-studio", "policy-studio"],
  ["mcp", "mcp-governance"],
  ["compliance", "compliance"],
  ["data-protection", "compliance"],
  ["audit", "audit-explorer"],
  ["reports", "reports"],
  ["dashboard", "dashboard"],
  ["settings", "settings"],
  ["ai-assist", "ai-assist"],
  ["client-api", "client-api-keys"],
  ["api-key", "client-api-keys"],
  ["prompt", "settings"],
  ["integration", "settings"],
  ["governance", "policy-studio"],
];

export function resolveHelpGuideSlug(slug: string): string {
  const normalized = slug.trim().toLowerCase();
  if (HELP_GUIDE_SLUG_ALIASES[normalized]) {
    return HELP_GUIDE_SLUG_ALIASES[normalized];
  }
  if (CANONICAL_HELP_GUIDE_SLUGS.has(normalized)) {
    return normalized;
  }
  for (const [prefix, target] of HELP_GUIDE_SLUG_PREFIX_RULES) {
    if (normalized === prefix || normalized.startsWith(`${prefix}-`)) {
      return target;
    }
  }
  return normalized;
}

export function normalizeHelpGuideHref(href: string): string {
  const match = href.match(/^\/help\/guides\/([^/?#]+)/);
  if (!match) return href;
  const resolved = resolveHelpGuideSlug(match[1]);
  if (!CANONICAL_HELP_GUIDE_SLUGS.has(resolved)) {
    return "/help?tab=guides";
  }
  return `/help/guides/${resolved}`;
}

export function helpGuideArticleHref(slug: string): string {
  return `/help/guides/${slug}`;
}

export function getHelpGuideArticle(slug: string): HelpGuideArticle | undefined {
  const resolved = resolveHelpGuideSlug(slug);
  return HELP_GUIDE_ARTICLES.find((article) => article.slug === resolved);
}

export function listHelpGuideSlugs(): string[] {
  return [...HELP_GUIDE_ARTICLES.map((article) => article.slug), ...Object.keys(HELP_GUIDE_SLUG_ALIASES)];
}

export const HELP_POLICIES = [
  { href: "/legal/security", label: "Security & trust", description: "Platform security posture and vulnerability reporting.", icon: Shield },
  { href: "/privacy", label: "Privacy policy", description: "How we handle personal and tenant data.", icon: BookOpen },
  { href: "/terms", label: "Terms & conditions", description: "Service terms for using PySetu AI.", icon: FileText },
  { href: "/cookies", label: "Cookie policy", description: "Cookies and local storage used by the product.", icon: Cookie },
] as const;

export const HELP_SUPPORT_EMAIL = "hello@pysetu.io";
