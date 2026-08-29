"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ClipboardList,
  FileCheck,
  Lock,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Zap,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MetricInsightModal } from "@/components/dashboard/metric-insight-modal";
import { ComplianceEvidencePanel } from "@/components/compliance/compliance-evidence-panel";
import { ComplianceFrameworkOverview } from "@/components/compliance/compliance-framework-overview";
import { FrameworkComplianceCard } from "@/components/compliance/framework-compliance-card";
import { GenaiEvidencePanel } from "@/components/compliance/genai-evidence-panel";
import { IacEvidencePanel } from "@/components/compliance/iac-evidence-panel";
import { PolicyExemptionPanel } from "@/components/compliance/policy-exemption-panel";
import { QuickLinkPills, SectionHeading } from "@/components/shared/section-chrome";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useComplianceFrameworks } from "@/hooks/use-compliance-frameworks";
import { useMetricInsight } from "@/hooks/use-metric-insight";
import type { ApiDashboardOverview } from "@/lib/api";

type Framework = ApiDashboardOverview["compliance_frameworks"][number];
type DetailTab = "frameworks" | "evidence" | "exemptions";

const QUICK_LINKS = [
  { href: "/reports", label: "Reports & Exports", icon: ClipboardList },
  { href: "/data-protection", label: "Data Protection", icon: Lock },
  { href: "/audit-explorer", label: "Audit Traces", icon: Search },
  { href: "/policy-studio", label: "Policy Studio", icon: Shield },
] as const;

const DETAIL_TABS: { id: DetailTab; label: string }[] = [
  { id: "frameworks", label: "Framework Controls & Audits" },
  { id: "evidence", label: "Automated Evidence & SIEM" },
  { id: "exemptions", label: "Break-Glass Policy Exemptions" },
];

const TAB_IDS = new Set<string>(DETAIL_TABS.map((t) => t.id));

export function ComplianceCenterView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedTab = searchParams.get("tab");
  const initialTab: DetailTab =
    requestedTab && TAB_IDS.has(requestedTab) ? (requestedTab as DetailTab) : "frameworks";

  const { data: frameworksData = [], isLoading, isError, refetch, isFetching } = useComplianceFrameworks();
  const [frameworkOverrides, setFrameworkOverrides] = useState<Record<string, Framework>>({});
  const [detailTab, setDetailTab] = useState<DetailTab>(initialTab);
  const {
    openMetricInsight,
    closeMetricInsight,
    insightOpen,
    activeContext,
    insightLoading,
    insight,
    insightError,
  } = useMetricInsight();

  const frameworks = useMemo(
    () => frameworksData.map((framework) => frameworkOverrides[framework.name] ?? framework),
    [frameworksData, frameworkOverrides]
  );

  const stats = useMemo(() => {
    const avgScore =
      frameworks.length > 0
        ? Math.round((frameworks.reduce((sum, f) => sum + f.score, 0) / frameworks.length) * 10) / 10
        : 0;
    const compliant = frameworks.filter((f) => f.status === "compliant").length;
    const totalControls = frameworks.reduce((sum, f) => sum + f.controls, 0);
    const passedControls = frameworks.reduce((sum, f) => sum + f.passed, 0);
    const openGaps = frameworks.reduce(
      (sum, f) => sum + (f.not_met ?? 0) + (f.in_progress ?? 0),
      0
    );
    const controlsMetPct = totalControls ? Math.round((passedControls / totalControls) * 100) : 0;
    return { avgScore, compliant, totalControls, passedControls, openGaps, controlsMetPct };
  }, [frameworks]);

  useEffect(() => {
    const next = searchParams.get("tab");
    if (next && TAB_IDS.has(next)) setDetailTab(next as DetailTab);
  }, [searchParams]);

  function selectTab(next: DetailTab) {
    setDetailTab(next);
    router.replace(`/compliance?tab=${next}`, { scroll: false });
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading compliance posture…</p>;
  }

  if (isError) {
    return (
      <div className="rounded-2xl border border-border/60 bg-muted/10 px-6 py-12 text-center">
        <p className="text-sm text-muted-foreground">
          Could not load compliance frameworks. Refresh the page or try again later.
        </p>
        <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="space-y-6">
        <QuickLinkPills links={QUICK_LINKS} />

        {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
        <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-6 shadow-sm">
          <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />

          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2.5 max-w-xl">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  Continuous Audit Mesh Active
                </Badge>
                <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                  <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                  EU AI Act & SOC2 Aligned
                </Badge>
                {isFetching && (
                  <Badge variant="outline" className="text-xs font-mono text-muted-foreground animate-pulse">
                    Evaluating Controls…
                  </Badge>
                )}
              </div>

              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
                Enterprise Compliance & Regulatory Posture
              </h1>
              <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                Automated continuous evaluation and evidence generation across EU AI Act, SOC 2 Type II, ISO 42001, HIPAA, and NIST AI Risk Management Framework.
              </p>
            </div>

            {/* Quick Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-3 shrink-0">
              <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Overall Score</span>
                  <FileCheck className="h-3.5 w-3.5 text-primary" />
                </div>
                <p className="mt-1.5 text-xl font-bold text-foreground">{stats.avgScore}%</p>
                <p className="text-[10px] text-muted-foreground">Weighted posture</p>
              </div>

              <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Compliant</span>
                  <Shield className="h-3.5 w-3.5 text-emerald-500" />
                </div>
                <p className="mt-1.5 text-xl font-bold text-emerald-600 dark:text-emerald-400">
                  {stats.compliant} / {frameworks.length}
                </p>
                <p className="text-[10px] text-muted-foreground">Frameworks certified</p>
              </div>

              <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Open Gaps</span>
                  <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />
                </div>
                <p className="mt-1.5 text-xl font-bold text-rose-600 dark:text-rose-400">{stats.openGaps}</p>
                <p className="text-[10px] text-muted-foreground">Requires remediation</p>
              </div>

              <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Controls Met</span>
                  <Zap className="h-3.5 w-3.5 text-blue-500" />
                </div>
                <p className="mt-1.5 text-xl font-bold text-blue-600 dark:text-blue-400">{stats.controlsMetPct}%</p>
                <p className="text-[10px] text-muted-foreground">Automated checks</p>
              </div>
            </div>
          </div>
        </div>

        {/* Framework Overview Section */}
        {frameworks.length > 0 && <ComplianceFrameworkOverview frameworks={frameworks} />}

        {/* ─── Navigation Tabs & Refresh ───────────────────────────────────────── */}
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs">
              {DETAIL_TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => selectTab(tab.id)}
                  className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                    detailTab === tab.id
                      ? "bg-primary text-primary-foreground shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs h-8"
              disabled={isFetching}
              onClick={() => refetch()}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
              Re-evaluate Controls
            </Button>
          </div>

          {detailTab === "frameworks" && (
            <div className="space-y-4">
              {frameworks.length === 0 ? (
                <p className="py-12 text-center text-sm text-muted-foreground">No compliance data available yet</p>
              ) : (
                <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
                  {frameworks.map((framework) => (
                    <FrameworkComplianceCard
                      key={framework.name}
                      framework={framework}
                      onFrameworkUpdated={(updated) =>
                        setFrameworkOverrides((current) => ({ ...current, [updated.name]: updated }))
                      }
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {detailTab === "evidence" && (
            <div className="space-y-4">
              <ComplianceEvidencePanel />
              <GenaiEvidencePanel />
              <IacEvidencePanel />
            </div>
          )}

          {detailTab === "exemptions" && <PolicyExemptionPanel />}
        </div>

        <MetricInsightModal
          open={insightOpen}
          loading={insightLoading}
          insight={insight}
          error={insightError}
          pendingTitle={activeContext?.cardTitle}
          onClose={closeMetricInsight}
        />
      </div>
    </TooltipProvider>
  );
}
