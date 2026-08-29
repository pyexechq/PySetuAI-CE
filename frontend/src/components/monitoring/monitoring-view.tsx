"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Activity, LayoutDashboard, Radar, Search, ShieldAlert, Zap, BarChart3, Clock, Sparkles } from "lucide-react";
import { MonitoringOverviewTab } from "@/components/monitoring/monitoring-overview-tab";
import { MonitoringSecurityTab } from "@/components/monitoring/monitoring-security-tab";
import { MonitoringTracesTab } from "@/components/monitoring/monitoring-traces-tab";
import { MonitoringDiscoverTab } from "@/components/monitoring/monitoring-discover-tab";
import { QuickLinkPills, SectionTabBar } from "@/components/shared/section-chrome";
import { Badge } from "@/components/ui/badge";
import { useAuthStore, type UserRole } from "@/stores/auth-store";

const QUICK_LINKS = [
  { href: "/", label: "Executive Dashboard", icon: LayoutDashboard },
  { href: "/audit-explorer", label: "Audit Explorer", icon: Search },
  { href: "/ai-gateway", label: "AI Gateway", icon: Zap },
] as const;

const tabs = [
  { id: "overview", label: "Overview & SLA", icon: Activity },
  { id: "security", label: "Threat Matrix & Security", icon: ShieldAlert },
  { id: "traces", label: "Distributed Traces", icon: Radar },
  { id: "discover", label: "AI Usage Discover", icon: Search },
] as const;

type MonitoringTab = (typeof tabs)[number]["id"];

const SECURITY_ROLES: UserRole[] = ["tenant_admin", "platform_admin", "security_admin", "auditor"];
const TRACES_ROLES: UserRole[] = ["tenant_admin", "platform_admin", "security_admin", "developer"];

function roleCanViewTab(role: UserRole | undefined, tab: MonitoringTab): boolean {
  if (!role) return false;
  if (tab === "overview") return true;
  if (tab === "security") return SECURITY_ROLES.includes(role);
  if (tab === "traces") return TRACES_ROLES.includes(role);
  if (tab === "discover") return SECURITY_ROLES.includes(role);
  return false;
}

export function MonitoringView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const user = useAuthStore((s) => s.user);
  const role = user?.role;

  const visibleTabs = useMemo(
    () => tabs.filter((tab) => roleCanViewTab(role, tab.id)),
    [role]
  );

  const requestedTab = (searchParams.get("tab") as MonitoringTab | null) ?? "overview";
  const defaultTab = visibleTabs[0]?.id ?? "overview";
  const activeTab = visibleTabs.some((t) => t.id === requestedTab) ? requestedTab : defaultTab;

  const [tab, setTab] = useState<MonitoringTab>(activeTab);

  useEffect(() => {
    setTab(activeTab);
  }, [activeTab]);

  function selectTab(next: MonitoringTab) {
    setTab(next);
    router.replace(`/monitoring?tab=${next}`, { scroll: false });
  }

  const sectionTabs = visibleTabs.map(({ id, label }) => ({ id, label }));

  return (
    <div className="space-y-6">
      <QuickLinkPills links={QUICK_LINKS} />

      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2.5 max-w-xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Live Ingestion Stream
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <Clock className="h-3.5 w-3.5 text-primary" />
                99.99% Gateway SLA
              </Badge>
              <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-xs font-mono">
                Sub-2ms Observability
              </Badge>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              Monitoring & Observability Hub
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Unified real-time visibility into AI gateway latencies, token compounding cost analytics, MITRE threat heatmaps, and distributed OpenTelemetry traces.
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        <SectionTabBar tabs={sectionTabs} active={tab} onChange={selectTab} />
      </div>

      {tab === "overview" && <MonitoringOverviewTab />}
      {tab === "security" && <MonitoringSecurityTab />}
      {tab === "traces" && <MonitoringTracesTab />}
      {tab === "discover" && <MonitoringDiscoverTab />}
    </div>
  );
}