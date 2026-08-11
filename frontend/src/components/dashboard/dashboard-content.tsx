"use client";

import { MetricCard } from "@/components/dashboard/metric-card";
import { TrafficChart } from "@/components/dashboard/traffic-chart";
import { RiskDonutChart } from "@/components/dashboard/risk-donut-chart";
import { TopThreatsList } from "@/components/dashboard/top-threats-list";
import { LlmUsageChart } from "@/components/dashboard/llm-usage-chart";
import { McpActivityTable } from "@/components/dashboard/mcp-activity-table";
import { CompliancePosture } from "@/components/dashboard/compliance-posture";
import { TopPoliciesTable } from "@/components/dashboard/top-policies-table";
import { TopAgentsTable } from "@/components/dashboard/top-agents-table";
import { useDashboardMetrics } from "@/hooks/use-dashboard-metrics";
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
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function DashboardContent() {
  const { data: metrics, isFetching: metricsFetching } = useDashboardMetrics();
  const { data: overview, isLoading, isFetching } = useDashboardOverview();
  const data = overview ?? EMPTY_DASHBOARD_OVERVIEW;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        {(isLoading || isFetching || metricsFetching) && (
          <Badge variant="outline" className="text-xs">
            Loading live data…
          </Badge>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <MetricCard title="Total AI Requests" value={metrics.totalRequests} change={metrics.totalRequestsChange} periodLabel={metrics.comparisonPeriod} icon={Activity} iconColor="text-blue-400" />
        <MetricCard title="Blocked Requests" value={metrics.blockedRequests} change={metrics.blockedRequestsChange} periodLabel={metrics.comparisonPeriod} invertTrend icon={ShieldAlert} iconColor="text-red-400" />
        <MetricCard title="Success Rate" value={metrics.successRate} change={metrics.successRateChange} periodLabel={metrics.comparisonPeriod} icon={CheckCircle2} iconColor="text-emerald-400" format="percent" />
        <MetricCard title="PII Redactions" value={metrics.piiRedactions} change={metrics.piiRedactionsChange} periodLabel={metrics.comparisonPeriod} invertTrend icon={ShieldCheck} iconColor="text-emerald-400" />
        <MetricCard title="Policy Violations" value={metrics.policyViolations} change={metrics.policyViolationsChange} periodLabel={metrics.comparisonPeriod} invertTrend icon={AlertTriangle} iconColor="text-amber-400" />
        <MetricCard title="MCP Violations" value={metrics.mcpViolations} change={metrics.mcpViolationsChange} periodLabel={metrics.comparisonPeriod} invertTrend icon={Server} iconColor="text-purple-400" />
        <MetricCard title="Total LLM Spend" value={metrics.costSavings} change={metrics.costSavingsChange} periodLabel={metrics.comparisonPeriod} icon={DollarSign} iconColor="text-emerald-400" format="currency" />
        <MetricCard title="Compliance Score" value={metrics.complianceScore} change={metrics.complianceScoreChange} periodLabel={metrics.comparisonPeriod} icon={FileCheck} iconColor="text-blue-400" format="percent" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TrafficChart data={data.traffic} />
        </div>
        <RiskDonutChart data={data.risk_distribution} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <TopPoliciesTable data={data.top_policies} />
        <TopAgentsTable data={data.top_agents} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <TopThreatsList data={data.top_threats} />
        <LlmUsageChart data={data.llm_usage} />
        <CompliancePosture data={data.compliance_frameworks} />
      </div>

      <McpActivityTable data={data.mcp_activity} />
    </div>
  );
}
