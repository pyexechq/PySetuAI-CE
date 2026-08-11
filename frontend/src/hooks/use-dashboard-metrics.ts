"use client";

import { useDashboardOverview, EMPTY_DASHBOARD_OVERVIEW } from "@/hooks/use-dashboard-overview";
import type { DashboardMetrics } from "@/lib/mock-data";

function mapMetrics(m: (typeof EMPTY_DASHBOARD_OVERVIEW)["metrics"]): DashboardMetrics {
  const successRate =
    m.success_rate ??
    (m.total_requests > 0
      ? Math.round(((m.total_requests - m.blocked_requests) / m.total_requests) * 1000) / 10
      : 0);

  return {
    totalRequests: m.total_requests,
    totalRequestsChange: m.total_requests_change_pct ?? 0,
    blockedRequests: m.blocked_requests,
    blockedRequestsChange: m.blocked_requests_change_pct ?? 0,
    piiRedactions: m.pii_redactions,
    piiRedactionsChange: m.pii_redactions_change_pct ?? 0,
    policyViolations: m.policy_violations,
    policyViolationsChange: m.policy_violations_change_pct ?? 0,
    mcpViolations: m.mcp_violations,
    mcpViolationsChange: m.mcp_violations_change_pct ?? 0,
    costSavings: m.cost_savings,
    costSavingsChange: 0,
    complianceScore: m.compliance_score,
    complianceScoreChange: m.compliance_score_change_pts ?? 0,
    successRate,
    successRateChange: m.success_rate_change_pts ?? 0,
    comparisonPeriod: m.comparison_period ?? "vs prior 30 days",
  };
}

export function useDashboardMetrics() {
  const query = useDashboardOverview();
  const metrics = mapMetrics(query.data?.metrics ?? EMPTY_DASHBOARD_OVERVIEW.metrics);

  return {
    ...query,
    data: metrics,
  };
}
