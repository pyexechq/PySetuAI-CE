"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Activity, Radar, ShieldAlert } from "lucide-react";
import { MonitoringOverviewTab } from "@/components/monitoring/monitoring-overview-tab";
import { MonitoringSecurityTab } from "@/components/monitoring/monitoring-security-tab";
import { MonitoringTracesTab } from "@/components/monitoring/monitoring-traces-tab";
import { cn } from "@/lib/utils";
import { useAuthStore, type UserRole } from "@/stores/auth-store";

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Monitoring</h1>
        <p className="text-sm text-muted-foreground">
          Unified gateway telemetry — operational health, AI security analytics, and request traces.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-border/60 pb-2">
        {visibleTabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => selectTab(id)}
            className={cn(
              "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              tab === id
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" && <MonitoringOverviewTab />}
      {tab === "security" && <MonitoringSecurityTab />}
      {tab === "traces" && <MonitoringTracesTab />}
    </div>
  );
}
