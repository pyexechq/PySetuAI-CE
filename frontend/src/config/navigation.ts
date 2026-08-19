import {
  LayoutDashboard,
  Shield,
  Server,
  Route,
  Workflow,
  GitBranch,
  Lock,
  FileCheck,
  Search,
  BarChart3,
  Settings,
  FlaskConical,
  ClipboardCheck,
  Radar,
  Bot,
  Monitor,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const mainNavGroups: NavGroup[] = [
  {
    label: "Home & ops",
    items: [
      { title: "Dashboard", href: "/", icon: LayoutDashboard },
      { title: "Monitoring", href: "/monitoring", icon: Radar },
      { title: "Audit Explorer", href: "/audit-explorer", icon: Search },
    ],
  },
  {
    label: "Gateway & routing",
    items: [
      { title: "AI Gateway", href: "/ai-gateway", icon: Shield },
      { title: "LLM Router", href: "/llm-router", icon: Route },
    ],
  },
  {
    label: "Governance",
    items: [
      { title: "Policy Studio", href: "/policy-studio", icon: Workflow },
      { title: "MCP Governance", href: "/mcp-governance", icon: Server },
      { title: "Governance Graph", href: "/governance-graph", icon: GitBranch },
      { title: "Governance Sandbox", href: "/studio", icon: FlaskConical },
    ],
  },
  {
    label: "Agents & endpoints",
    items: [
      { title: "Agent Inventory", href: "/agents", icon: Bot },
      { title: "Endpoint Security", href: "/endpoints", icon: Monitor },
      { title: "MCP Tool Chains", href: "/mcp-tool-chains", icon: GitBranch },
    ],
  },
  {
    label: "Risk & compliance",
    items: [
      { title: "Compliance", href: "/compliance", icon: FileCheck },
      { title: "Data Protection", href: "/data-protection", icon: Lock },
      { title: "Approval Center", href: "/approvals", icon: ShieldCheck },
      { title: "Reports", href: "/reports", icon: BarChart3 },
    ],
  },
  {
    label: "Platform",
    items: [
      { title: "QA Dashboard", href: "/qa-dashboard", icon: ClipboardCheck },
      { title: "Settings", href: "/settings", icon: Settings },
    ],
  },
];

/** Flat list preserved for route checks and legacy imports. */
export const mainNavItems: NavItem[] = mainNavGroups.flatMap((group) => group.items);
