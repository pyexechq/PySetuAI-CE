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
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/dashboard/metric-card";
import { MetricInsightModal } from "@/components/dashboard/metric-insight-modal";
import { ComplianceEvidencePanel } from "@/components/compliance/compliance-evidence-panel";
import { ComplianceFrameworkOverview } from "@/components/compliance/compliance-framework-overview";
import { FrameworkComplianceCard } from "@/components/compliance/framework-compliance-card";
import { GenaiEvidencePanel } from "@/components/compliance/genai-evidence-panel";
import { IacEvidencePanel } from "@/components/compliance/iac-evidence-panel";
import { PolicyExemptionPanel } from "@/components/compliance/policy-exemption-panel";
import { QuickLinkPills, SectionHeading, SectionTabBar } from "@/components/shared/section-chrome";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useComplianceFrameworks } from "@/hooks/use-compliance-frameworks";
import { useMetricInsight } from "@/hooks/use-metric-insight";
import type { ApiDashboardOverview } from "@/lib/api";

type Framework = ApiDashboardOverview["compliance_frameworks"][number];
type DetailTab = "frameworks" | "evidence" | "exemptions";

const QUICK_LINKS = [
  { href: "/reports", label: "Reports", icon: ClipboardList },
  { href: "/data-protection", label: "Data Protection", icon: Lock },
  { href: "/audit-explorer", label: "Audit Explorer", icon: Search },
  { href: "/policy-studio", label: "Policy Studio", icon: Shield },
] as const;

const DETAIL_TABS: { id: DetailTab; label: string }[] = [
  { id: "frameworks", label: "Frameworks" },
  { id: "evidence", label: "Evidence & exports" },
  { id: "exemptions", label: "Break-glass" },
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
      <div className="rounded-lg border border-border/60 bg-muted/10 px-6 py-12 text-center">
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
      <div className="space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <QuickLinkPills links={QUICK_LINKS} />
          <div className="flex items-center gap-2">
            {isFetching && (
              <Badge variant="outline" className="text-xs font-normal">
                Syncing…
              </Badge>
            )}
            <Button variant="outline" size="sm" className="h-8 w-8 p-0" disabled={isFetching} onClick={() => refetch()}>
              <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
              <span className="sr-only">Refresh all frameworks</span>
            </Button>
          </div>
        </div>

        <section className="space-y-3">
          <SectionHeading title="At a glance" />
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              variant="hero"
              showTrend={false}
              title="Compliance Score"
              value={stats.avgScore}
              change={0}
              icon={FileCheck}
              iconColor="text-blue-400"
              format="percent"
              insightKey="compliance_score"
              onInsightClick={openMetricInsight}
            />
            <MetricCard
              variant="hero"
              showTrend={false}
              title="Frameworks compliant"
              value={`${stats.compliant}/${frameworks.length}`}
              change={0}
              icon={Shield}
              iconColor="text-emerald-400"
              format="raw"
            />
            <MetricCard
              variant="hero"
              showTrend={false}
              title="Open gaps"
              value={stats.openGaps}
              change={0}
              invertTrend
              icon={ShieldAlert}
              iconColor="text-red-400"
            />
            <MetricCard
              variant="hero"
              showTrend={false}
              title="Controls met"
              value={`${stats.controlsMetPct}%`}
              change={0}
              icon={FileCheck}
              iconColor="text-violet-400"
              format="raw"
            />
          </div>
        </section>

        {frameworks.length > 0 && <ComplianceFrameworkOverview frameworks={frameworks} />}

        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeading title="Compliance operations" />
            <SectionTabBar tabs={DETAIL_TABS} active={detailTab} onChange={selectTab} />
          </div>

          {detailTab === "frameworks" && (
            <>
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
              <p className="text-xs text-muted-foreground">
                Re-evaluate a framework after policy changes, then use manual fix or AI assist on each open control.
              </p>
            </>
          )}

          {detailTab === "evidence" && (
            <div className="space-y-4">
              <ComplianceEvidencePanel />
              <GenaiEvidencePanel />
              <IacEvidencePanel />
            </div>
          )}

          {detailTab === "exemptions" && <PolicyExemptionPanel />}
        </section>

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
