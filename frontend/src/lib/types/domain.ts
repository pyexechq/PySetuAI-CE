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
  endpointUrl?: string | null;
  requests: number;
  percentage: number;
  latency: number;
  successRate: number;
  isActive?: boolean;
  apiKeySet?: boolean;
  apiKeyMasked?: string | null;
  costPer1mInput?: number;
  costPer1mOutput?: number;
  modelAliases?: string[];
  color: string;
}

export interface RoutingRule {
  id: string;
  name: string;
  priority: number;
  condition: string;
  targetModel: string;
  status: "active" | "draft" | "disabled";
  responseFormat: "openai" | "anthropic" | "vertex" | "auto";
  targetProvider?: string | null;
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
    catalog_slug?: string;
    portal_visible?: boolean;
    allowed_agents?: string[];
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
  has_request_log?: boolean;
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
  cost_optimization?: CompoundingCostSummary | null;
}

export interface CompoundingCostLayer {
  id: string;
  label: string;
  tokens_saved: number;
  estimated_usd: number;
  requests: number;
  share_pct: number;
}

export interface CompoundingCostSummary {
  layers: CompoundingCostLayer[];
  total_tokens_saved: number;
  total_estimated_usd: number;
  narrative: string;
}

export interface PromptVersion {
  id: string;
  template_id: string;
  version: number;
  system_prompt: string;
  variables: string[];
  created_by?: string;
  created_at: string;
}

export interface PromptTemplate {
  id: string;
  tenant_id: string;
  name: string;
  alias?: string | null;
  description?: string | null;
  enforce_mode: "strict" | "warn" | "disabled";
  is_active: boolean;
  current_version_id?: string | null;
  current_version?: PromptVersion | null;
  created_at: string;
  updated_at: string;
}

export interface PromptTemplateCreate {
  name: string;
  alias?: string | null;
  description?: string | null;
  enforce_mode: "strict" | "warn" | "disabled";
  system_prompt: string;
}

export interface PromptTemplateUpdate {
  name?: string;
  alias?: string | null;
  description?: string | null;
  enforce_mode?: "strict" | "warn" | "disabled";
  is_active?: boolean;
}

export interface PromptVersionCreate {
  system_prompt: string;
}

export interface CustomIntent {
  id: string;
  tenant_id: string;
  name: string;
  description?: string | null;
  action: "block" | "monitor" | "redact";
  keywords: string[];
  confidence_threshold: number;
  is_active: boolean;
  parent_id?: string | null;
  intent_type?: "intent" | "folder";
  created_at: string;
  updated_at: string;
}

export interface CustomIntentCreate {
  name: string;
  description?: string;
  action: "block" | "monitor" | "redact";
  keywords: string[];
  confidence_threshold: number;
  is_active?: boolean;
  parent_id?: string | null;
  intent_type?: "intent" | "folder";
}

export interface CustomIntentUpdate {
  name?: string;
  description?: string;
  action?: "block" | "monitor" | "redact";
  keywords?: string[];
  confidence_threshold?: number;
  is_active?: boolean;
  parent_id?: string | null;
  intent_type?: "intent" | "folder";
}

export interface CustomIntentMatch {
  intent_id: string;
  intent_name: string;
  action: string;
  matched_keywords: string[];
  score: number;
}

export interface CustomIntentTestResponse {
  matched: boolean;
  matches: CustomIntentMatch[];
  action: string;
  modified_prompt?: string | null;
}
