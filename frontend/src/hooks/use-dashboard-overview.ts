"use client";

import { useQuery } from "@tanstack/react-query";
import { api, type ApiDashboardOverview } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export const EMPTY_DASHBOARD_OVERVIEW: ApiDashboardOverview = {
  metrics: {
    total_requests: 0,
    blocked_requests: 0,
    pii_redactions: 0,
    policy_violations: 0,
    mcp_violations: 0,
    cost_savings: 0,
    compliance_score: 0,
    success_rate: 0,
    agentic_security_events: 0,
    mcp_tool_chain_events: 0,
    total_requests_change_pct: 0,
    blocked_requests_change_pct: 0,
    pii_redactions_change_pct: 0,
    policy_violations_change_pct: 0,
    mcp_violations_change_pct: 0,
    agentic_security_events_change_pct: 0,
    mcp_tool_chain_events_change_pct: 0,
    compliance_score_change_pts: 0,
    success_rate_change_pts: 0,
    comparison_period: "vs prior 30 days",
  },
  traffic: [],
  risk_distribution: [],
  top_threats: [],
  llm_usage: [],
  mcp_activity: [],
  top_policies: [],
  top_agents: [],
  compliance_frameworks: [],
  security_trends: [],
  token_saving: {
    requests_compressed: 0,
    original_tokens: 0,
    compressed_tokens: 0,
    tokens_saved: 0,
    savings_pct: 0,
  },
};

export function useDashboardOverview() {
  const token = useAuthStore((s) => s.token);

  return useQuery({
    queryKey: ["dashboard-overview", token],
    queryFn: () => api.getDashboardOverview(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });
}

export function mapSecurityTrends(overview: ApiDashboardOverview) {
  return overview.security_trends.map((point) => ({
    date: point.date,
    blocked: point.blocked,
    allowed: point.allowed,
    underReview: point.under_review,
  }));
}

export function buildDataClassifications(overview: ApiDashboardOverview) {
  const { metrics } = overview;
  const allowed = Math.max(0, metrics.total_requests - metrics.blocked_requests);
  const slices = [
    { label: "Allowed", count: allowed, color: "#22c55e" },
    { label: "Blocked", count: metrics.blocked_requests, color: "#ef4444" },
    { label: "PII redacted", count: metrics.pii_redactions, color: "#f97316" },
    { label: "Under review", count: metrics.policy_violations, color: "#eab308" },
  ].filter((slice) => slice.count > 0);

  const total = slices.reduce((sum, slice) => sum + slice.count, 0) || 1;
  return slices.map((slice) => ({
    ...slice,
    percentage: Math.round((slice.count / total) * 100),
  }));
}
