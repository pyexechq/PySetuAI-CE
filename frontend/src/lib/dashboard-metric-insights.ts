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

export const DASHBOARD_METRIC_TOOLTIP = "View AI summary & insights";
