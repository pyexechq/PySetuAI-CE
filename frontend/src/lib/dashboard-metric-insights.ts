export type DashboardMetricKey =
  | "total_requests"
  | "blocked_requests"
  | "success_rate"
  | "pii_redactions"
  | "policy_violations"
  | "mcp_violations"
  | "cost_savings"
  | "compliance_score"
  | "protocol_translations"
  | "provider_migrations"
  | "translation_cost_savings"
  | "legacy_app_compatibility";

export interface MetricInsightClickContext {
  cardTitle: string;
  displayValue: string;
  periodLabel?: string;
  change?: number;
}

export type MetricInsightClickHandler = (
  metricKey: DashboardMetricKey,
  context: MetricInsightClickContext
) => void;

export const DASHBOARD_METRIC_TOOLTIP = "View AI summary & insights";

/** Exact card/KPI titles mapped to backend insight keys. */
const EXACT_METRIC_TITLE_KEYS: Record<string, DashboardMetricKey> = {
  "Total AI Requests": "total_requests",
  "Events (range)": "total_requests",
  "AI Requests": "total_requests",
  "Success Rate": "success_rate",
  "Success rate": "legacy_app_compatibility",
  "Compliance Score": "compliance_score",
  "Blocked Requests": "blocked_requests",
  "Block rate": "blocked_requests",
  "Threats blocked (30d)": "blocked_requests",
  "Policy Blocks": "blocked_requests",
  "Blocked": "blocked_requests",
  "Allowed": "success_rate",
  "Allowed Actions": "success_rate",
  "PII Redactions": "pii_redactions",
  "Policy Violations": "policy_violations",
  "High-Risk Events": "policy_violations",
  "MCP Violations": "mcp_violations",
  "Total LLM Spend": "cost_savings",
  "Stacked cost savings": "translation_cost_savings",
  "Total translations": "protocol_translations",
  "Failed": "protocol_translations",
  "Legacy App Compatibility": "legacy_app_compatibility",
};

export function resolveMetricInsightKey(title: string): DashboardMetricKey | undefined {
  const trimmed = title.trim();
  if (trimmed in EXACT_METRIC_TITLE_KEYS) {
    return EXACT_METRIC_TITLE_KEYS[trimmed];
  }
  return undefined;
}
