"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Activity, LayoutDashboard, Radar, Search, ShieldAlert } from "lucide-react";
import { MonitoringOverviewTab } from "@/components/monitoring/monitoring-overview-tab";
import { MonitoringSecurityTab } from "@/components/monitoring/monitoring-security-tab";
import { MonitoringTracesTab } from "@/components/monitoring/monitoring-traces-tab";
import { QuickLinkPills, SectionTabBar } from "@/components/shared/section-chrome";
import { useAuthStore, type UserRole } from "@/stores/auth-store";

const QUICK_LINKS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/audit-explorer", label: "Audit Explorer", icon: Search },
] as const;

const tabs = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "security", label: "Security", icon: ShieldAlert },
  { id: "traces", label: "Traces", icon: Radar },
] as const;

type MonitoringTab = (typeof tabs)[number]["id"];

const SECURITY_ROLES: UserRole[] = ["tenant_admin", "platform_admin", "security_admin", "auditor"];
const TRACES_ROLES: UserRole[] = ["tenant_admin", "platform_admin", "security_admin", "developer"];

function roleCanViewTab(role: UserRole | undefined, tab: MonitoringTab): boolean {
  if (!role) return false;
  if (tab === "overview") return true;
  if (tab === "security") return SECURITY_ROLES.includes(role);
  if (tab === "traces") return TRACES_ROLES.includes(role);
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
    <div className="space-y-8">
      <QuickLinkPills links={QUICK_LINKS} />
      <SectionTabBar tabs={sectionTabs} active={tab} onChange={selectTab} />

      {tab === "overview" && <MonitoringOverviewTab />}
      {tab === "security" && <MonitoringSecurityTab />}
      {tab === "traces" && <MonitoringTracesTab />}
    </div>
  );
}