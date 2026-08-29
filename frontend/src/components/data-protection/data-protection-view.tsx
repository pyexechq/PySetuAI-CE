"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { LayoutDashboard, Lock, ShieldCheck, Globe, Zap, FileCheck, Layers, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataResidencyMap } from "@/components/data-protection/data-residency-map";
import { DlpScannerTab } from "@/components/data-protection/dlp-scanner-tab";
import { DataMovementPolicyPanel } from "@/components/data-protection/data-movement-policy-panel";
import { PolicyExemptionPanel } from "@/components/compliance/policy-exemption-panel";
import { QuickLinkPills } from "@/components/shared/section-chrome";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { formatNumber } from "@/lib/utils";

type DataProtectionTab = "overview" | "dlp-scanner" | "movement-policy" | "exemptions";

const QUICK_LINKS = [
  { href: "/ai-gateway", label: "AI Gateway", icon: Zap },
  { href: "/compliance", label: "Compliance Posture", icon: FileCheck },
  { href: "/policy-studio", label: "Policy Studio", icon: ShieldCheck },
] as const;

const TABS: { id: DataProtectionTab; label: string }[] = [
  { id: "overview", label: "Classification & Residency" },
  { id: "dlp-scanner", label: "DLP Scanner & Entities" },
  { id: "movement-policy", label: "Data Movement Policies" },
  { id: "exemptions", label: "Policy Exemptions" },
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
    <div className="space-y-6">
      <QuickLinkPills links={QUICK_LINKS} />

      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-teal-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2.5 max-w-xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Presidio PII Redaction Mesh Active
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <Globe className="h-3.5 w-3.5 text-primary" />
                Geo-Fenced Data Movement
              </Badge>
              <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-xs font-mono">
                Sub-2ms DLP Scan
              </Badge>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              Data Protection & Residency Guardrails
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Real-time bidirectional PII masking, cryptographic data tokenization, sovereign boundary enforcement, and dynamic DLP rule evaluation across global AI traffic.
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-3 shrink-0">
            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Total Scanned</span>
                <ShieldCheck className="h-3.5 w-3.5 text-primary" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-foreground">{formatNumber(data?.total_scanned ?? total)}</p>
              <p className="text-[10px] text-muted-foreground">Inspected payloads</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">PII Redactions</span>
                <Lock className="h-3.5 w-3.5 text-emerald-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-emerald-600 dark:text-emerald-400">{formatNumber(data?.pii_redactions ?? 0)}</p>
              <p className="text-[10px] text-muted-foreground">Entities masked</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Active Regions</span>
                <Globe className="h-3.5 w-3.5 text-blue-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-blue-600 dark:text-blue-400">{regions.length}</p>
              <p className="text-[10px] text-muted-foreground">Sovereign zones</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Classifications</span>
                <Layers className="h-3.5 w-3.5 text-amber-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-amber-600 dark:text-amber-400">{dataClassifications.length}</p>
              <p className="text-[10px] text-muted-foreground">Active categories</p>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Navigation Tabs ──────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => selectTab(tab.id)}
                className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === tab.id
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {activeTab === "overview" && (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="border-border/80 bg-card/60 rounded-2xl shadow-xs">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold">Classification Inventory</CardTitle>
                <CardDescription className="text-xs">Distribution of detected PII, financial, and confidential data classes.</CardDescription>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <p className="py-16 text-center text-xs text-muted-foreground font-mono">Scanning classification repository…</p>
                ) : dataClassifications.length === 0 ? (
                  <p className="py-16 text-center text-xs text-muted-foreground">No classified events in this period</p>
                ) : (
                  <>
                    <ResponsiveContainer width="100%" height={260}>
                      <PieChart>
                        <Pie
                          data={dataClassifications}
                          dataKey="count"
                          nameKey="label"
                          cx="50%"
                          cy="50%"
                          innerRadius={65}
                          outerRadius={95}
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
                            borderRadius: "12px",
                            fontSize: "12px",
                          }}
                          formatter={(value) => formatNumber(Number(value))}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="mt-4 grid grid-cols-2 gap-2.5">
                      {dataClassifications.map((item) => (
                        <div key={item.label} className="flex items-center gap-2 p-2 rounded-xl bg-muted/20 border border-border/50">
                          <div className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                          <div className="min-w-0">
                            <p className="text-xs font-semibold text-foreground truncate">{item.label}</p>
                            <p className="text-[10px] text-muted-foreground font-mono">
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

            <Card className="border-border/80 bg-card/60 rounded-2xl shadow-xs">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold">Data Residency Geo-Fence</CardTitle>
                <CardDescription className="text-xs">Sovereign routing boundaries and local edge nodes.</CardDescription>
              </CardHeader>
              <CardContent>
                <DataResidencyMap regions={regions} />
                <div className="mt-3 p-3 rounded-xl bg-muted/20 border border-border/50 text-center text-xs text-muted-foreground">
                  Total scanned events: <span className="font-bold text-foreground">{formatNumber(data?.total_scanned ?? total)}</span> · PII redactions:{" "}
                  <span className="font-bold text-emerald-600 dark:text-emerald-400">{formatNumber(data?.pii_redactions ?? 0)}</span>
                </div>
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
    </div>
  );
}
