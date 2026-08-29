import {
  Building2,
  FileText,
  Globe,
  KeyRound,
  Layers,
  Network,
  Shield,
  ShieldCheck,
  Sparkles,
  Sun,
  Users,
  type LucideIcon,
} from "lucide-react";

export type SettingsGroup = "general" | "platform" | "access";

export interface SettingsNavItem {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  description: string;
  group: SettingsGroup;
}

export const SETTINGS_GROUP_LABELS: Record<SettingsGroup, string> = {
  general: "Workspace",
  platform: "AI & integrations",
  access: "Access & identity",
};

export const settingsNavItems: SettingsNavItem[] = [
  {
    id: "organization",
    label: "Organization",
    href: "/settings/organization",
    icon: Building2,
    description: "Tenant profile, branding, and module visibility",
    group: "general",
  },
  {
    id: "appearance",
    label: "Appearance",
    href: "/settings/appearance",
    icon: Sun,
    description: "Theme and display preferences",
    group: "general",
  },
  {
    id: "integrations",
    label: "Integrations",
    href: "/settings/integrations",
    icon: KeyRound,
    description: "Vault, Pinecone vector store, and alert webhooks",
    group: "platform",
  },
  {
    id: "ai-assist",
    label: "AI Assist",
    href: "/settings/ai-assist",
    icon: Sparkles,
    description: "Platform AI Assist and tenant default LLM provider keys",
    group: "platform",
  },
  {
    id: "gateway",
    label: "Gateway limits",
    href: "/settings/gateway",
    icon: Network,
    description: "Tenant-wide rate limits, token saving default, token budgets, and API origins",
    group: "platform",
  },
  {
    id: "edge-gateways",
    label: "Edge Gateway Mesh",
    href: "/ai-gateway?tab=edge-mesh",
    icon: Globe,
    description: "Multi-region edge gateway nodes, VPC data planes, and sub-2ms local OPA DLP execution",
    group: "platform",
  },
  {
    id: "sanctioned-ai",
    label: "Sanctioned AI",
    href: "/settings/sanctioned-ai",
    icon: ShieldCheck,
    description: "Explicitly allowlisted AI tools and shadow-AI discovery",
    group: "platform",
  },
  {
    id: "prompts",
    label: "Prompt templates",
    href: "/settings/prompts",
    icon: FileText,
    description: "Managed system prompts and enforce modes",
    group: "platform",
  },
  {
    id: "policy-bundles",
    label: "Policy bundles",
    href: "/settings/policy-bundles",
    icon: Layers,
    description: "Group policies for gateway ingress",
    group: "access",
  },
  {
    id: "api-keys",
    label: "Client API keys",
    href: "/settings/api-keys",
    icon: KeyRound,
    description: "Ingress keys, limits, and token saving per application",
    group: "access",
  },
  {
    id: "identity",
    label: "Identity / SSO",
    href: "/settings/identity",
    icon: Shield,
    description: "Login domains and OIDC provider configuration",
    group: "access",
  },
  {
    id: "users",
    label: "Users & RBAC",
    href: "/settings/users",
    icon: Users,
    description: "Tenant users, roles, and permissions",
    group: "access",
  },
];

export function settingsItemsForGroup(group: SettingsGroup): SettingsNavItem[] {
  return settingsNavItems.filter((item) => item.group === group);
}

export function findSettingsSection(pathname: string): SettingsNavItem | undefined {
  return settingsNavItems.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
}
