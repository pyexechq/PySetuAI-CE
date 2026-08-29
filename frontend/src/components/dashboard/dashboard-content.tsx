"use client";

import { useState } from "react";
import { MetricCard } from "@/components/dashboard/metric-card";
import { MetricInsightModal } from "@/components/dashboard/metric-insight-modal";
import { TrafficChart } from "@/components/dashboard/traffic-chart";
import { LlmUsageChart } from "@/components/dashboard/llm-usage-chart";
import { TokenSavingCard } from "@/components/dashboard/token-saving-card";
import { CostAnalyticsCard } from "@/components/dashboard/cost-analytics-card";
import { McpActivityTable } from "@/components/dashboard/mcp-activity-table";
import { TopPoliciesTable } from "@/components/dashboard/top-policies-table";
import { TopAgentsTable } from "@/components/dashboard/top-agents-table";
import { RiskDonutChart } from "@/components/dashboard/risk-donut-chart";
import { QuickLinkPills } from "@/components/shared/section-chrome";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { useDashboardMetrics } from "@/hooks/use-dashboard-metrics";
import { useMetricInsight } from "@/hooks/use-metric-insight";
import { EMPTY_DASHBOARD_OVERVIEW, useDashboardOverview } from "@/hooks/use-dashboard-overview";
import {
  Activity,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Server,
  DollarSign,
  FileCheck,
  CheckCircle2,
  ArrowRightLeft,
  Lock,
  Radar,
  Bot,
  Workflow,
  Sparkles,
  Zap,
  TrendingUp,
} from "lucide-react";

const QUICK_LINKS = [
  { href: "/ai-gateway", label: "AI Gateway", icon: Zap },
  { href: "/llm-router", label: "LLM Router", icon: ArrowRightLeft },
  { href: "/policy-studio", label: "Policy Studio", icon: ShieldCheck },
  { href: "/audit-explorer", label: "Audit Traces", icon: Radar },
  { href: "/mcp-governance", label: "MCP Governance", icon: Server },
] as const;

type DetailTab = "governance" | "usage" | "cost" | "mcp";

const DETAIL_TABS: { id: DetailTab; label: string; icon: typeof ShieldCheck }[] = [
  { id: "governance", label: "Governance & Risk", icon: ShieldCheck },
  { id: "usage", label: "LLM Traffic & Models", icon: Activity },
  { id: "cost", label: "Cost Arbitrage ROI", icon: DollarSign },
  { id: "mcp", label: "Agentic & MCP Fleet", icon: Server },
];

export function DashboardContent() {
  const { data: metrics, isFetching: metricsFetching } = useDashboardMetrics();
  const { data: overview, isLoading, isFetching } = useDashboardOverview();
  const data = overview ?? EMPTY_DASHBOARD_OVERVIEW;

  const [detailTab, setDetailTab] = useState<DetailTab>("governance");
  const {
    openMetricInsight,
    closeMetricInsight,
    insightOpen,
    activeContext,
    insightLoading,
    insight,
    insightError,
  } = useMetricInsight();

  const isLiveLoading = isLoading || isFetching || metricsFetching;
  const periodLabel = metrics.comparisonPeriod;

  return (
    <TooltipProvider delayDuration={200}>
      <div className="space-y-6">
        <QuickLinkPills links={QUICK_LINKS} />

        {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
        <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-4 sm:p-6 shadow-sm">
          {/* Subtle Background Glow */}
          <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

          <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between w-full min-w-0">
            <div className="space-y-2.5 w-full min-w-0 max-w-xl">
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  All Security Mesh Systems Operational
                </Badge>
                <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                  <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                  Real-time DLP + OPA + Vault Active
                </Badge>
                {isLiveLoading && (
                  <Badge variant="outline" className="text-xs font-mono text-muted-foreground animate-pulse">
                    Syncing Live Telemetry…
                  </Badge>
                )}
              </div>

              <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-foreground break-words">
                Executive AI Command & Governance Center
              </h1>
              <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                Centralized telemetry across your entire enterprise AI stack — tracking gateway traffic, cost arbitrage savings, compliance adherence, and agentic tool safety.
              </p>
            </div>

            {/* Quick KPI Highlights */}
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-2.5 sm:gap-3 w-full lg:w-auto shrink-0">
              <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Total Requests</span>
                  <Activity className="h-3.5 w-3.5 text-primary" />
                </div>
                <p className="mt-1.5 text-lg sm:text-xl font-bold text-foreground">{metrics.totalRequests}</p>
                <p className="text-[10px] text-muted-foreground">{periodLabel}</p>
              </div>

              <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Success Rate</span>
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                </div>
                <p className="mt-1.5 text-lg sm:text-xl font-bold text-emerald-600 dark:text-emerald-400">{metrics.successRate}%</p>
                <p className="text-[10px] text-muted-foreground">Gateway throughput</p>
              </div>

              <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Threats Blocked</span>
                  <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />
                </div>
                <p className="mt-1.5 text-lg sm:text-xl font-bold text-rose-600 dark:text-rose-400">{metrics.blockedRequests}</p>
                <p className="text-[10px] text-muted-foreground">Injections & PII</p>
              </div>

              <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Compliance Score</span>
                  <FileCheck className="h-3.5 w-3.5 text-blue-500" />
                </div>
                <p className="mt-1.5 text-lg sm:text-xl font-bold text-blue-600 dark:text-blue-400">{metrics.complianceScore}%</p>
                <p className="text-[10px] text-muted-foreground">EU AI Act & SOC2</p>
              </div>
            </div>
          </div>
        </div>

        {/* ─── Segmented Tabs ───────────────────────────────────────────────────── */}
        <div className="flex items-center gap-1.5 overflow-x-auto p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs">
          {DETAIL_TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setDetailTab(tab.id)}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all whitespace-nowrap shrink-0 ${
                  detailTab === tab.id
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab 1: Governance & Risk */}
        {detailTab === "governance" && (
          <div className="grid gap-6 lg:grid-cols-12">
            <div className="lg:col-span-8 space-y-6">
              <TrafficChart data={data.traffic} />
              <TopPoliciesTable data={data.top_policies} />
            </div>
            <div className="lg:col-span-4 space-y-6">
              <RiskDonutChart data={data.risk_distribution} />
              <TokenSavingCard />
            </div>
          </div>
        )}

        {/* Tab 2: LLM Traffic & Models */}
        {detailTab === "usage" && (
          <div className="grid gap-6 lg:grid-cols-12">
            <div className="lg:col-span-8">
              <LlmUsageChart data={data.llm_usage} />
            </div>
            <div className="lg:col-span-4">
              <TokenSavingCard />
            </div>
          </div>
        )}

        {/* Tab 3: Cost Arbitrage ROI */}
        {detailTab === "cost" && (
          <div className="grid gap-6 lg:grid-cols-12">
            <div className="lg:col-span-8">
              <CostAnalyticsCard />
            </div>
            <div className="lg:col-span-4">
              <TokenSavingCard />
            </div>
          </div>
        )}

        {/* Tab 4: Agentic & MCP Fleet */}
        {detailTab === "mcp" && (
          <div className="grid gap-6 lg:grid-cols-12">
            <div className="lg:col-span-6">
              <TopAgentsTable data={data.top_agents} />
            </div>
            <div className="lg:col-span-6">
              <McpActivityTable data={data.mcp_activity} />
            </div>
          </div>
        )}

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
