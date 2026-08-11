import {
  LayoutDashboard,
  Shield,
  Server,
  Route,
  Workflow,
  GitBranch,
  Lock,
  Activity,
  FileCheck,
  Search,
  BarChart3,
  Settings,
  FlaskConical,
  AlertTriangle,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
}

export const mainNavItems: NavItem[] = [
  { title: "Dashboard", href: "/", icon: LayoutDashboard },
  { title: "AI Gateway", href: "/ai-gateway", icon: Shield },
  { title: "MCP Governance", href: "/mcp-governance", icon: Server },
  { title: "LLM Router", href: "/llm-router", icon: Route },
  { title: "Policy Studio", href: "/policy-studio", icon: Workflow },
  { title: "Governance Graph", href: "/governance-graph", icon: GitBranch },
  { title: "Data Protection", href: "/data-protection", icon: Lock },
  { title: "Observability", href: "/observability", icon: Activity },
  { title: "Compliance", href: "/compliance", icon: FileCheck },
  { title: "Security Center", href: "/security", icon: AlertTriangle },
  { title: "Audit Explorer", href: "/audit-explorer", icon: Search },
  { title: "Studio", href: "/studio", icon: FlaskConical },
  { title: "Reports", href: "/reports", icon: BarChart3 },
  { title: "Settings", href: "/settings", icon: Settings },
];
