"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { LayoutDashboard } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DataResidencyMap } from "@/components/data-protection/data-residency-map";
import { DlpScannerTab } from "@/components/data-protection/dlp-scanner-tab";
import { DataMovementPolicyPanel } from "@/components/data-protection/data-movement-policy-panel";
import { PolicyExemptionPanel } from "@/components/compliance/policy-exemption-panel";
import { SectionTabBar } from "@/components/shared/section-chrome";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { formatNumber } from "@/lib/utils";

type DataProtectionTab = "overview" | "dlp-scanner" | "movement-policy" | "exemptions";

const TABS: { id: DataProtectionTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "dlp-scanner", label: "DLP Scanner" },
  { id: "movement-policy", label: "Movement Policy" },
  { id: "exemptions", label: "Exemptions" },
];

const TAB_IDS = new Set<string>(TABS.map((t) => t.id));

const POLICY_EDIT_ROLES = ["tenant_admin", "security_admin", "platform_admin"];

export function DataProtectionView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedTab = searchParams.get("tab");
  const initialTab: DataProtectionTab =
    requestedTab && TAB_IDS.has(requestedTab) ? (requestedTab as DataProtectionTab) : "overview";

  const [activeTab, setActiveTab] = useState<DataProtectionTab>(initialTab);
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const canEditPolicy = Boolean(user?.role && POLICY_EDIT_ROLES.includes(user.role));

  const { data, isLoading } = useQuery({
    queryKey: ["data-protection-overview", token],
    queryFn: () => api.getDataProtectionOverview(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  useEffect(() => {
    const next = searchParams.get("tab");
    if (next && TAB_IDS.has(next)) setActiveTab(next as DataProtectionTab);
  }, [searchParams]);

  function selectTab(next: DataProtectionTab) {
    setActiveTab(next);
    router.replace(`/data-protection?tab=${next}`, { scroll: false });
  }

  const dataClassifications = data?.classifications ?? [];
  const regions = data?.regions ?? [];
  const total = dataClassifications.reduce((sum, d) => sum + d.count, 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionTabBar tabs={TABS} active={activeTab} onChange={selectTab} />
        {activeTab === "overview" && (
          <Button variant="outline" size="sm" className="gap-1.5" asChild>
            <Link href="/">
              <LayoutDashboard className="h-3.5 w-3.5" />
              Dashboard KPIs
            </Link>
          </Button>
        )}
      </div>

      {activeTab === "overview" && (
        <div className="grid gap-4 lg:grid-cols-2">
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle>Classification Inventory</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="py-16 text-center text-sm text-muted-foreground">Loading classification data…</p>
          ) : dataClassifications.length === 0 ? (
            <p className="py-16 text-center text-sm text-muted-foreground">No classified events in this period</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={dataClassifications}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={110}
                    paddingAngle={3}
                  >
                    {dataClassifications.map((entry) => (
                      <Cell key={entry.label} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                    formatter={(value) => formatNumber(Number(value))}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-4 grid grid-cols-2 gap-3">
                {dataClassifications.map((item) => (
                  <div key={item.label} className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                    <div>
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatNumber(item.count)} ({item.percentage}%)
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle>Data Residency Map</CardTitle>
        </CardHeader>
        <CardContent>
          <DataResidencyMap regions={regions} />
          <p className="mt-3 text-center text-sm text-muted-foreground">
            Total scanned events: {formatNumber(data?.total_scanned ?? total)} · PII redactions:{" "}
            {formatNumber(data?.pii_redactions ?? 0)}
          </p>
        </CardContent>
      </Card>
        </div>
      )}

      {activeTab === "dlp-scanner" && <DlpScannerTab token={token} />}

      {activeTab === "movement-policy" && (
        <DataMovementPolicyPanel token={token} canEdit={canEditPolicy} onSaved={() => {}} />
      )}

      {activeTab === "exemptions" && <PolicyExemptionPanel />}
    </div>
  );
}

