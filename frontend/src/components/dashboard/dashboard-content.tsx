"use client";

import { useState } from "react";
import { MetricCard, MetricStrip } from "@/components/dashboard/metric-card";
import { MetricInsightModal } from "@/components/dashboard/metric-insight-modal";
import { TrafficChart } from "@/components/dashboard/traffic-chart";
import { LlmUsageChart } from "@/components/dashboard/llm-usage-chart";
import { TokenSavingCard } from "@/components/dashboard/token-saving-card";
import { CostAnalyticsCard } from "@/components/dashboard/cost-analytics-card";
import { McpActivityTable } from "@/components/dashboard/mcp-activity-table";
import { TopPoliciesTable } from "@/components/dashboard/top-policies-table";
import { TopAgentsTable } from "@/components/dashboard/top-agents-table";
import { RiskDonutChart } from "@/components/dashboard/risk-donut-chart";
import { QuickLinkPills, SectionTabBar } from "@/components/shared/section-chrome";
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
} from "lucide-react";

const QUICK_LINKS = [
  { href: "/monitoring", label: "Monitoring", icon: Radar },
  { href: "/compliance", label: "Compliance", icon: FileCheck },
  { href: "/data-protection", label: "Data Protection", icon: Lock },
  { href: "/ai-gateway?tab=compatibility", label: "Compatibility", icon: ArrowRightLeft },
] as const;

type DetailTab = "governance" | "usage" | "cost" | "mcp";

const DETAIL_TABS: { id: DetailTab; label: string }[] = [
  { id: "governance", label: "Governance" },
  { id: "usage", label: "LLM usage" },
  { id: "cost", label: "Cost & savings" },
  { id: "mcp", label: "MCP activity" },
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
      <div className="space-y-8">
        {/* Quick nav + live indicator */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <QuickLinkPills links={QUICK_LINKS} />
          {isLiveLoading && (
            <Badge variant="outline" className="text-xs font-normal">
              Syncing…
            </Badge>
          )}
        </div>

        {/* Primary KPIs */}
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">At a glance</h2>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              variant="hero"
              title="Total AI Requests"
              value={metrics.totalRequests}
              change={metrics.totalRequestsChange}
              periodLabel={periodLabel}
              icon={Activity}
              iconColor="text-blue-400"
              insightKey="total_requests"
              onInsightClick={openMetricInsight}
            />
            <MetricCard
              variant="hero"
              title="Success Rate"
              value={metrics.successRate}
              change={metrics.successRateChange}
              periodLabel={periodLabel}
              icon={CheckCircle2}
              iconColor="text-emerald-400"
              format="percent"
              insightKey="success_rate"
              onInsightClick={openMetricInsight}
            />
            <MetricCard
              variant="hero"
              title="Compliance Score"
              value={metrics.complianceScore}
              change={0}
              showTrend={false}
              icon={FileCheck}
              iconColor="text-blue-400"
              format="percent"
              insightKey="compliance_score"
              onInsightClick={openMetricInsight}
            />
            <MetricCard
              variant="hero"
              title="Blocked Requests"
              value={metrics.blockedRequests}
              change={metrics.blockedRequestsChange}
              periodLabel={periodLabel}
              invertTrend
              icon={ShieldAlert}
              iconColor="text-red-400"
              insightKey="blocked_requests"
              onInsightClick={openMetricInsight}
            />
          </div>
        </section>

        {/* Secondary risk strip */}
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Risk & spend</h2>
          <MetricStrip
            onInsightClick={openMetricInsight}
            items={[
              {
                title: "PII Redactions",
                value: metrics.piiRedactions,
                change: metrics.piiRedactionsChange,
                periodLabel,
                invertTrend: true,
                icon: ShieldCheck,
                iconColor: "text-teal-400",
                insightKey: "pii_redactions",
              },
              {
                title: "Policy Violations",
                value: metrics.policyViolations,
                change: metrics.policyViolationsChange,
                periodLabel,
                invertTrend: true,
                icon: AlertTriangle,
                iconColor: "text-amber-400",
                insightKey: "policy_violations",
              },
              {
                title: "MCP Violations",
                value: metrics.mcpViolations,
                change: metrics.mcpViolationsChange,
                periodLabel,
                invertTrend: true,
                icon: Server,
                iconColor: "text-violet-400",
                insightKey: "mcp_violations",
              },
              {
                title: "Agentic Security Events",
                value: metrics.agenticSecurityEvents,
                change: metrics.agenticSecurityEventsChange,
                periodLabel,
                invertTrend: true,
                icon: Bot,
                iconColor: "text-rose-400",
                insightKey: "agentic_security_events",
              },
              {
                title: "MCP Tool Chain Events",
                value: metrics.mcpToolChainEvents,
                change: metrics.mcpToolChainEventsChange,
                periodLabel,
                invertTrend: true,
                icon: Workflow,
                iconColor: "text-sky-400",
                insightKey: "mcp_tool_chain_events",
              },
              {
                title: "Total LLM Spend",
                value: metrics.costSavings,
                change: metrics.costSavingsChange,
                periodLabel,
                icon: DollarSign,
                iconColor: "text-emerald-400",
                format: "currency",
                insightKey: "cost_savings",
              },
            ]}
          />
        </section>

        {/* Traffic + risk distribution */}
        <section className="grid gap-4 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <TrafficChart data={data.traffic} />
          </div>
          <div className="lg:col-span-4">
            <RiskDonutChart data={data.risk_distribution} />
          </div>
        </section>

        {/* Tabbed detail — one section visible at a time */}
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">Operational detail</h2>
            <SectionTabBar tabs={DETAIL_TABS} active={detailTab} onChange={setDetailTab} />
          </div>

          {detailTab === "governance" && (
            <div className="grid gap-4 lg:grid-cols-2">
              <TopPoliciesTable data={data.top_policies} />
              <TopAgentsTable data={data.top_agents} />
            </div>
          )}

          {detailTab === "usage" && <LlmUsageChart data={data.llm_usage} summary={data.llm_usage_summary} />}

          {detailTab === "cost" && (
            <div className="grid gap-4 lg:grid-cols-2">
              <CostAnalyticsCard />
              <TokenSavingCard data={data.token_saving} />
            </div>
          )}

          {detailTab === "mcp" && <McpActivityTable data={data.mcp_activity} />}
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
