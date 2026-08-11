export interface DashboardMetrics {
  totalRequests: number;
  totalRequestsChange: number;
  blockedRequests: number;
  blockedRequestsChange: number;
  piiRedactions: number;
  piiRedactionsChange: number;
  policyViolations: number;
  policyViolationsChange: number;
  mcpViolations: number;
  mcpViolationsChange: number;
  costSavings: number;
  costSavingsChange: number;
  complianceScore: number;
  complianceScoreChange: number;
  successRate: number;
  successRateChange: number;
  comparisonPeriod?: string;
}

export interface PolicyTreeNode {
  id: string;
  label: string;
  type: "folder" | "policy";
  status?: "active" | "draft" | "disabled";
  children?: PolicyTreeNode[];
}

export interface PolicyRule {
  id: string;
  name: string;
  condition: string;
  action: string;
  severity: "low" | "medium" | "high" | "critical";
  enabled: boolean;
}

export interface GovernanceNode {
  id: string;
  label: string;
  type: string;
  x: number;
  y: number;
  color: string;
  status?: string;
}

export interface GovernanceEdge {
  from: string;
  to: string;
  label: string;
  correlation: string;
}

export interface RoutingModel {
  id?: string;
  model: string;
  providerType?: string;
  requests: number;
  percentage: number;
  latency: number;
  successRate: number;
  isActive?: boolean;
  apiKeySet?: boolean;
  apiKeyMasked?: string | null;
  color: string;
}

export interface RoutingRule {
  id: string;
  name: string;
  priority: number;
  condition: string;
  targetModel: string;
  status: "active" | "draft" | "disabled";
}

export interface McpServer {
  id: string;
  name: string;
  category: string;
  successRate: number;
  avgLatency: number;
  totalCalls: number;
  status: "healthy" | "degraded" | "offline";
  tools: number;
  toolNames: string[];
  endpointUrl: string | null;
  transport: string;
  connectionConfig: {
    auth_header?: string;
    timeout_sec?: number;
    tool_schemas?: {
      name: string;
      description?: string | null;
      inputSchema?: Record<string, unknown> | null;
    }[];
    mcp_session?: {
      state?: string;
      session_id?: string;
      initialized_at?: string;
      protocol_version?: string;
      server_info?: { name?: string; version?: string };
    };
  };
  trustScore: number;
  riskScore: number;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource: string;
  status: "allowed" | "blocked" | "review";
  risk: "low" | "medium" | "high";
  details: string;
}

export interface DataClassification {
  label: string;
  count: number;
  percentage: number;
  color: string;
}

export interface DataResidencyRegion {
  id: string;
  name: string;
  percentage: number;
  records: number;
  status: "compliant" | "review" | "at-risk";
  color: string;
  hubs: string[];
  policy: string;
}

export interface SecurityTrendPoint {
  date: string;
  blocked: number;
  allowed: number;
  underReview: number;
}

export interface ReportKpi {
  label: string;
  value: string;
  change: string;
  trend: "up" | "down" | "flat";
}

export interface ReportCatalogEntry {
  id: string;
  report_uuid?: string;
  name: string;
  description: string;
  category: string;
  frequency: string;
  format: string;
  last_generated: string;
  status: "ready" | "scheduled" | "generating";
  query?: { source: string; filters: Record<string, unknown>; limit: number };
  schedule?: {
    enabled: boolean;
    frequency: string;
    time: string;
    day_of_week: number | null;
    day_of_month: number | null;
    next_run_at: string | null;
    recipients?: string[];
  };
  is_builtin?: boolean;
}

export interface ExecutiveSummary {
  period: string;
  kpis: ReportKpi[];
  compliance_score: number;
  frameworks_compliant: number;
  frameworks_total: number;
  top_risks: string[];
}
