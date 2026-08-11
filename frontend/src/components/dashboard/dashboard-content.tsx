"use client";

import Link from "next/link";
import { useState } from "react";
import { MetricCard } from "@/components/dashboard/metric-card";
import { MetricInsightModal } from "@/components/dashboard/metric-insight-modal";
import { TrafficChart } from "@/components/dashboard/traffic-chart";
import { LlmUsageChart } from "@/components/dashboard/llm-usage-chart";
import { McpActivityTable } from "@/components/dashboard/mcp-activity-table";
import { TopPoliciesTable } from "@/components/dashboard/top-policies-table";
import { TopAgentsTable } from "@/components/dashboard/top-agents-table";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useDashboardMetrics } from "@/hooks/use-dashboard-metrics";
import { EMPTY_DASHBOARD_OVERVIEW, useDashboardOverview } from "@/hooks/use-dashboard-overview";
import { ApiError, api, type ApiDashboardMetricInsight } from "@/lib/api";
import type { DashboardMetricKey } from "@/lib/dashboard-metric-insights";
import { useAuthStore } from "@/stores/auth-store";
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
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

const DRILL_DOWN_LINKS = [
  { href: "/monitoring", label: "Monitoring", description: "Volume, latency, security & traces" },
  { href: "/compliance", label: "Compliance Center", description: "Framework scores & remediation" },
  { href: "/data-protection", label: "Data Protection", description: "Classification & residency map" },
  { href: "/compatibility-center", label: "Compatibility Center", description: "UAG mappings & translation stats" },
] as const;

export function DashboardContent() {
  const token = useAuthStore((s) => s.token);
  const { data: metrics, isFetching: metricsFetching } = useDashboardMetrics();
  const { data: overview, isLoading, isFetching } = useDashboardOverview();
  const data = overview ?? EMPTY_DASHBOARD_OVERVIEW;

  const [activeMetric, setActiveMetric] = useState<DashboardMetricKey | null>(null);
  const [insightLoading, setInsightLoading] = useState(false);
  const [insight, setInsight] = useState<ApiDashboardMetricInsight | null>(null);
  const [insightError, setInsightError] = useState<string | null>(null);

  async function openMetricInsight(metricKey: DashboardMetricKey) {
    if (!token) return;
    (document.activeElement as HTMLElement | null)?.blur();
    setActiveMetric(metricKey);
    setInsightLoading(true);
    setInsight(null);
    setInsightError(null);
    try {
      const result = await api.getDashboardMetricInsight(token, metricKey);
      setInsight(result);
    } catch (err) {
      setInsightError(err instanceof ApiError ? err.message : "Unable to load metric insights.");
    } finally {
      setInsightLoading(false);
    }
  }

  function closeMetricInsight() {
    setActiveMetric(null);
    setInsight(null);
    setInsightError(null);
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          {(isLoading || isFetching || metricsFetching) && (
            <Badge variant="outline" className="text-xs">
              Loading live data…
            </Badge>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <MetricCard title="Total AI Requests" value={metrics.totalRequests} change={metrics.totalRequestsChange} periodLabel={metrics.comparisonPeriod} icon={Activity} iconColor="text-blue-400" insightKey="total_requests" onInsightClick={openMetricInsight} />
          <MetricCard title="Blocked Requests" value={metrics.blockedRequests} change={metrics.blockedRequestsChange} periodLabel={metrics.comparisonPeriod} invertTrend icon={ShieldAlert} iconColor="text-red-400" insightKey="blocked_requests" onInsightClick={openMetricInsight} />
          <MetricCard title="Success Rate" value={metrics.successRate} change={metrics.successRateChange} periodLabel={metrics.comparisonPeriod} icon={CheckCircle2} iconColor="text-emerald-400" format="percent" insightKey="success_rate" onInsightClick={openMetricInsight} />
          <MetricCard title="PII Redactions" value={metrics.piiRedactions} change={metrics.piiRedactionsChange} periodLabel={metrics.comparisonPeriod} invertTrend icon={ShieldCheck} iconColor="text-emerald-400" insightKey="pii_redactions" onInsightClick={openMetricInsight} />
          <MetricCard title="Policy Violations" value={metrics.policyViolations} change={metrics.policyViolationsChange} periodLabel={metrics.comparisonPeriod} invertTrend icon={AlertTriangle} iconColor="text-amber-400" insightKey="policy_violations" onInsightClick={openMetricInsight} />
          <MetricCard title="MCP Violations" value={metrics.mcpViolations} change={metrics.mcpViolationsChange} periodLabel={metrics.comparisonPeriod} invertTrend icon={Server} iconColor="text-purple-400" insightKey="mcp_violations" onInsightClick={openMetricInsight} />
          <MetricCard title="Total LLM Spend" value={metrics.costSavings} change={metrics.costSavingsChange} periodLabel={metrics.comparisonPeriod} icon={DollarSign} iconColor="text-emerald-400" format="currency" insightKey="cost_savings" onInsightClick={openMetricInsight} />
          <MetricCard title="Compliance Score" value={metrics.complianceScore} change={metrics.complianceScoreChange} periodLabel={metrics.comparisonPeriod} icon={FileCheck} iconColor="text-blue-400" format="percent" insightKey="compliance_score" onInsightClick={openMetricInsight} />
        </div>

        <Card className="border-border/60 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Radar className="h-4 w-4" />
              Drill down
            </CardTitle>
            <CardDescription>
              Detailed charts and admin tools live in dedicated modules — use the links below instead of duplicating them here.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {DRILL_DOWN_LINKS.map((item) => (
              <Button
                key={item.href}
                variant="outline"
                className="h-auto flex-col items-start gap-1 px-3 py-3 text-left"
                asChild
              >
                <Link href={item.href}>
                  <span className="flex items-center gap-1.5 text-sm font-medium">
                    {item.href === "/data-protection" && <Lock className="h-3.5 w-3.5" />}
                    {item.href === "/compatibility-center" && <ArrowRightLeft className="h-3.5 w-3.5" />}
                    {item.href === "/monitoring" && <Radar className="h-3.5 w-3.5" />}
                    {item.href === "/compliance" && <FileCheck className="h-3.5 w-3.5" />}
                    {item.label}
                  </span>
                  <span className="text-xs font-normal text-muted-foreground">{item.description}</span>
                </Link>
              </Button>
            ))}
          </CardContent>
        </Card>

        <TrafficChart data={data.traffic} />

        <div className="grid gap-4 lg:grid-cols-2">
          <TopPoliciesTable data={data.top_policies} />
          <TopAgentsTable data={data.top_agents} />
        </div>

        <LlmUsageChart data={data.llm_usage} summary={data.llm_usage_summary} />

        <McpActivityTable data={data.mcp_activity} />

        <MetricInsightModal
          open={activeMetric !== null}
          loading={insightLoading}
          insight={insight}
          error={insightError}
          onClose={closeMetricInsight}
        />
      </div>
    </TooltipProvider>
  );
}
