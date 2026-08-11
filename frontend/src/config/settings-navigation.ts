import {
  ArrowRightLeft,
  Building2,
  KeyRound,
  Layers,
  Shield,
  Sparkles,
  Sun,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface SettingsNavItem {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  description: string;
}

export const settingsNavItems: SettingsNavItem[] = [
  {
    id: "organization",
    label: "Organization",
    href: "/settings/organization",
    icon: Building2,
    description: "Tenant profile and signed-in account",
  },
  {
    id: "integrations",
    label: "Integrations",
    href: "/settings/integrations",
    icon: KeyRound,
    description: "OpenAI, Gemini, Ollama, and alert webhooks",
  },
  {
    id: "ai-assist",
    label: "AI Assist",
    href: "/settings/ai-assist",
    icon: Sparkles,
    description: "Platform-wide AI key for Policy Studio, Compliance, and insights",
  },
  {
    id: "uag",
    label: "Universal AI Gateway",
    href: "/settings/uag",
    icon: ArrowRightLeft,
    description: "Provider mappings and translation policies",
  },
  {
    id: "identity",
    label: "Identity / SSO",
    href: "/settings/identity",
    icon: Shield,
    description: "OIDC provider configuration (Phase 5a)",
  },
  {
    id: "policy-bundles",
    label: "Policy Bundles",
    href: "/settings/policy-bundles",
    icon: Layers,
    description: "Group policies for gateway ingress",
  },
  {
    id: "api-keys",
    label: "Client API Keys",
    href: "/settings/api-keys",
    icon: KeyRound,
    description: "Ingress keys for applications",
  },
  {
    id: "users",
    label: "Users & RBAC",
    href: "/settings/users",
    icon: Users,
    description: "Tenant users, roles, and permissions",
  },
  {
    id: "appearance",
    label: "Appearance",
    href: "/settings/appearance",
    icon: Sun,
    description: "Theme and display preferences",
  },
];
