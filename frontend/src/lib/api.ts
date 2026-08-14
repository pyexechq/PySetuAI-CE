import { handleSessionExpired } from "@/lib/session";
import type {
  PromptTemplate,
  PromptVersion,
  CustomIntent,
  CustomIntentCreate,
  CustomIntentUpdate,
  CustomIntentTestResponse,
} from "./types/domain";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001/api/v1";

export interface ApiDateRangeParams {
  from_date?: string;
  to_date?: string;
}

function appendDateRange(query: URLSearchParams, params?: ApiDateRangeParams) {
  if (params?.from_date) query.set("from_date", params.from_date);
  if (params?.to_date) query.set("to_date", params.to_date);
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function formatApiErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: string }).msg);
        }
        return null;
      })
      .filter((item): item is string => Boolean(item));
    if (messages.length > 0) return messages.join("; ");
  }
  return fallback;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    let message = text;
    try {
      const json = JSON.parse(text) as { error?: { message?: string }; detail?: unknown };
      message =
        json.error?.message ??
        formatApiErrorDetail(json.detail, text || `Request failed (${response.status})`);
    } catch {
      // keep raw text
    }
    if (response.status === 401) {
      handleSessionExpired();
      throw new ApiError("Session expired. Please sign in again.", 401);
    }
    throw new ApiError(message || `Request failed (${response.status})`, response.status);
  }

  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text.trim()) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers ?? {}),
  };

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  return parseResponse<T>(response);
}

export interface ApiDashboardMetrics {
  total_requests: number;
  blocked_requests: number;
  pii_redactions: number;
  policy_violations: number;
  mcp_violations: number;
  cost_savings: number;
  compliance_score: number;
  success_rate?: number;
  total_requests_change_pct?: number;
  blocked_requests_change_pct?: number;
  pii_redactions_change_pct?: number;
  policy_violations_change_pct?: number;
  mcp_violations_change_pct?: number;
  compliance_score_change_pts?: number;
  success_rate_change_pts?: number;
  comparison_period?: string;
}

export interface ApiComplianceControl {
  id: string;
  title: string;
  requirement: string;
  status: "met" | "not_met" | "in_progress";
  evidence?: string | null;
  remediation?: string | null;
  pysetu_module?: string | null;
}

export interface ApiComplianceSnapshotSummary {
  id: string;
  created_at: string;
  created_by_name: string;
  period_start: string;
  period_end: string;
  overall_score: number;
  frameworks_compliant: number;
  frameworks_total: number;
  notes: string;
}

export interface ApiComplianceSnapshotDetail extends ApiComplianceSnapshotSummary {
  frameworks: ApiDashboardOverview["compliance_frameworks"];
}

export interface ApiGenaiEvidenceSummary {
  id: string;
  created_at: string;
  actor: string;
  bundle_type: string;
  allowed: boolean;
  highest_sensitivity: string | null;
  destination?: string | null;
  blocked_hop?: string | null;
}

export interface ApiRagGatewaySettings {
  pinecone_enabled: boolean;
  pinecone_api_key_set: boolean;
  pinecone_api_key_masked: string | null;
  pinecone_host: string;
  pinecone_namespace: string;
  pinecone_dimension: number;
  embedding_model: string;
  configured: boolean;
  config_source: string;
  env_fallback_note: string;
}

export interface ApiRagMovementResponse {
  allowed: boolean;
  classifications: string[];
  sensitivity_labels: string[];
  highest_sensitivity: string | null;
  movement: Record<string, string>;
  violations: { rule: string; message: string; severity: string }[];
  evidence_bundle_id: string | null;
  stub_note: string | null;
  exemption_applied?: boolean;
  exemption_error?: string | null;
}

export interface ApiRagIngestResponse {
  allowed: boolean;
  blocked_hop: string | null;
  hops: {
    hop: string;
    movement_from: string;
    movement_to: string;
    operation: string;
    allowed: boolean;
    blocked_locally: boolean;
  }[];
  classifications: string[];
  sensitivity_labels: string[];
  highest_sensitivity: string | null;
  vector_id: string | null;
  upserted: boolean;
  embedding_source: string | null;
  evidence_bundle_id: string | null;
  note: string | null;
  exemption_applied?: boolean;
  exemption_error?: string | null;
}

export interface ApiIacEvidenceReport {
  id: string;
  generated_at: string;
  scanner: string;
  deploy_root: string;
  files_scanned: number;
  score: number;
  summary: { pass: number; warn: number; fail: number };
  checks: {
    id: string;
    title: string;
    framework: string;
    status: string;
    evidence_files: string[];
    detail: string;
  }[];
}

export interface ApiPolicyExemption {
  id: string;
  created_by: string;
  reason: string;
  ticket_ref: string | null;
  allowed_destinations: string[];
  expires_at: string;
  revoked_at: string | null;
  use_count: number;
  max_uses: number | null;
  created_at: string;
  status: string;
}

export interface ApiComplianceReevaluateResponse {
  framework: ApiDashboardOverview["compliance_frameworks"][number];
  evaluated_at: string;
}

export interface ApiComplianceRemediationResponse {
  control_id: string;
  framework_name: string;
  framework_slug: string;
  mode: "manual" | "ai";
  summary: string;
  steps: string[];
  manual_route?: string | null;
  module_name?: string | null;
  evidence?: string | null;
  ai_generated: boolean;
  estimated_effort?: string | null;
  generated_at: string;
}

export interface ApiMetricInsightContext {
  card_title?: string;
  display_value?: string;
  period_label?: string;
  change?: number;
}

export interface ApiDashboardMetricInsight {
  metric_key: string;
  title: string;
  summary: string;
  insights: string[];
  recommended_actions: string[];
  ai_generated: boolean;
  generated_at: string;
}

export interface ApiDashboardOverview {
  metrics: ApiDashboardMetrics;
  traffic: { date: string; total_requests: number; blocked_requests: number }[];
  risk_distribution: { level: string; count: number; percentage: number }[];
  top_threats: { name: string; count: number }[];
  llm_usage: {
    model: string;
    percentage: number;
    requests: number;
    total_tokens: number;
    avg_tokens_per_request: number;
    cost_usd: number;
  }[];
  llm_usage_summary?: {
    total_tokens: number;
    token_utilization_pct: number;
    avg_burn_usd_per_day: number;
    total_cost_usd: number;
    monthly_token_quota: number;
  };
  mcp_activity: { server: string; total_calls: number; blocked: number; risk: string }[];
  top_policies: { rank: number; name: string; requests: number; violations: number; enforcement: string }[];
  top_agents: { rank: number; name: string; requests: number; success_rate: number; avg_latency: number }[];
  compliance_frameworks: {
    name: string;
    score: number;
    status: string;
    controls: number;
    passed: number;
    in_progress?: number;
    not_met?: number;
    control_items?: ApiComplianceControl[];
  }[];
  security_trends: { date: string; blocked: number; allowed: number; under_review: number }[];
  uag?: {
    protocol_translations: number;
    provider_migrations: number;
    cost_savings_usd: number;
    legacy_app_compatibility: number;
    route_breakdown: { route: string; count: number }[];
  };
  token_saving?: {
    requests_compressed: number;
    original_tokens: number;
    compressed_tokens: number;
    tokens_saved: number;
    savings_pct: number;
  };
}

export interface ApiCostAnalyticsBucket {
  key: string;
  label: string;
  requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface ApiCostAnalytics {
  generated_at: string;
  period_days: number;
  summary: {
    requests: number;
    total_tokens: number;
    total_cost_usd: number;
    avg_cost_per_request_usd: number;
    avg_tokens_per_request: number;
  };
  by_model: ApiCostAnalyticsBucket[];
  by_user: ApiCostAnalyticsBucket[];
  by_team: ApiCostAnalyticsBucket[];
  daily_trend: Array<{ date: string; requests: number; total_tokens: number; cost_usd: number }>;
}

export interface ApiUser {
  id: string;
  email: string;
  name: string;
  role: string;
  tenant_id: string;
}

export interface ApiTenantUser {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
}

export interface ApiTenantUserUpdate {
  role?: string;
  is_active?: boolean;
}

export interface ApiTenantUserCreate {
  email: string;
  name: string;
  password: string;
  role?: string;
}

export interface ApiRbacPermissions {
  role: string;
  permissions: string[];
}

export interface ApiRbacMatrix {
  permissions: string[];
  roles: string[];
  matrix: Record<string, Record<string, boolean>>;
}

export interface ApiTokenResponse {
  access_token: string;
  token_type: string;
}

export interface ApiPlatformConfig {
  enabled: boolean;
  deployment_mode: string;
  platform_tenant_slug: string;
}

export interface ApiPublicSiteConfig {
  slug: string;
  name: string;
  display_name: string;
  logo_url: string | null;
  brand_tagline: string;
  subdomain: string;
  entry_mode: "login_only" | "marketing_site";
  login_path: string;
  tenant_url: string;
}

export interface ApiTenantFeatures {
  qa_dashboard: boolean;
  compatibility_center: boolean;
  governance_sandbox: boolean;
  reports: boolean;
}

export interface ApiTenantFeaturePolicyEntry {
  tenant_editable: boolean;
}

export type ApiTenantFeaturePolicy = Record<keyof ApiTenantFeatures, ApiTenantFeaturePolicyEntry>;

export interface ApiPlatformTenant {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string | null;
  demo_data_loaded: boolean;
  admin_email: string | null;
  subdomain: string;
  entry_mode: "login_only" | "marketing_site";
  tenant_url: string;
  features: ApiTenantFeatures;
  feature_policy: ApiTenantFeaturePolicy;
}

export interface ApiPlatformTenantCreateRequest {
  name: string;
  slug: string;
  admin_email: string;
  admin_name: string;
  admin_password?: string;
  send_admin_invite?: boolean;
  send_invite_email?: boolean;
  invite_template_slug?: string;
  include_demo_data?: boolean;
  is_active?: boolean;
  subdomain?: string;
  entry_mode?: "login_only" | "marketing_site";
}

export interface ApiPlatformTenantUpdateRequest {
  name?: string;
  is_active?: boolean;
  subdomain?: string;
  entry_mode?: "login_only" | "marketing_site";
  features?: Partial<ApiTenantFeatures>;
  feature_policy?: Partial<ApiTenantFeaturePolicy>;
}

export interface ApiPlatformTenantInvite {
  id: string;
  tenant_id: string;
  email: string;
  role: string;
  expires_at: string | null;
  accepted_at: string | null;
  invite_url: string;
  email_template_slug?: string | null;
  email_sent?: boolean;
  email_status?: string | null;
  email_sent_at?: string | null;
  email_reason?: string | null;
}

export interface ApiInviteEmailTemplate {
  slug: string;
  name: string;
  description: string;
  subject: string;
  html_body: string;
  text_body: string;
  category: string;
  is_builtin: boolean;
  variables: string[];
  updated_at: string | null;
}

export interface ApiInviteEmailPreview {
  template_slug: string;
  subject: string;
  html_body: string;
  text_body: string;
}

export interface ApiPlatformTenantProvisionResult {
  tenant: ApiPlatformTenant;
  demo_users: { email: string; name: string; role: string; password: string }[];
  message: string;
  admin_invite?: ApiPlatformTenantInvite | null;
}

export interface ApiPlatformOpsDependency {
  status: string;
  error?: string | null;
}

export interface ApiPlatformOpsOverview {
  generated_at: string;
  status: string;
  fleet: {
    total_tenants: number;
    active_tenants: number;
    suspended_tenants: number;
    llm_requests_today: number;
    llm_blocked_today: number;
    fleet_block_rate_pct: number;
    audit_events_today: number;
    avg_latency_ms: number;
  };
  dependencies: {
    database: ApiPlatformOpsDependency;
    opa: ApiPlatformOpsDependency;
  };
  tenants: {
    id: string;
    name: string;
    slug: string;
    is_active: boolean;
    admin_email: string | null;
    demo_data_loaded: boolean;
    subdomain: string;
    llm_requests_today: number;
    llm_blocked_today: number;
    block_rate_pct: number;
    audit_events_today: number;
    audit_blocked_today: number;
    avg_latency_ms: number;
    p95_latency_ms: number;
  }[];
}

export interface ApiPlatformUsageOverview {
  generated_at: string;
  period_days: number;
  fleet: {
    total_tenants: number;
    active_tenants: number;
    llm_requests: number;
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    avg_tokens_per_request: number;
  };
  tenants: {
    id: string;
    name: string;
    slug: string;
    is_active: boolean;
    admin_email: string | null;
    llm_requests: number;
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    avg_tokens_per_request: number;
  }[];
}

export interface ApiInvitePreview {
  email: string;
  role: string;
  tenant_name: string;
  tenant_slug: string;
  expires_at: string;
}

export interface ApiAcceptInviteResult {
  access_token: string;
  token_type: string;
  tenant_slug: string;
  tenant_url: string;
}

export interface LoginPayload {
  email: string;
  password: string;
  tenant_slug?: string;
}

export interface ApiIdentitySettings {
  oidc_jit_provision_enabled: boolean;
  platform_jit_default: boolean;
  allowed_login_domains: string[] | null;
}

export interface ApiIdentitySettingsUpdate {
  oidc_jit_provision_enabled?: boolean;
  allowed_login_domains?: string[] | null;
}

export interface ApiGatewaySettings {
  ai_rate_limit_rpm: number | null;
  ai_rate_limit_rph: number | null;
  ai_rate_limit_rpd: number | null;
  ai_token_limit_tpm: number | null;
  ai_token_limit_tph: number | null;
  ai_token_limit_tpd: number | null;
  ai_token_budgets: Record<string, any> | null;
  allowed_api_origins: string[] | null;
  token_saving_enabled: boolean;
  token_saving_mode: string;
}

export interface ApiGatewaySettingsUpdate {
  ai_rate_limit_rpm?: number | null;
  ai_rate_limit_rph?: number | null;
  ai_rate_limit_rpd?: number | null;
  ai_token_limit_tpm?: number | null;
  ai_token_limit_tph?: number | null;
  ai_token_limit_tpd?: number | null;
  allowed_api_origins?: string[] | null;
  token_saving_enabled?: boolean;
  token_saving_mode?: string;
}

export const api = {
  login: (payload: LoginPayload) =>
    apiFetch<ApiTokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: payload.email,
        password: payload.password,
        tenant_slug: payload.tenant_slug ?? "acme",
      }),
    }),

  getCurrentUser: (token: string) =>
    apiFetch<ApiUser>("/auth/me", {}, token),

  updateCurrentUser: (token: string, data: { name: string }) =>
    apiFetch<ApiUser>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    }, token),

  getOrganizationSettings: (token: string) =>
    apiFetch<ApiOrganizationSettings>("/settings/organization", {}, token),

  updateOrganizationSettings: (
    token: string,
    body: {
      name?: string;
      display_name?: string;
      logo_url?: string;
      brand_tagline?: string;
      qa_dashboard_enabled?: boolean;
      features?: Partial<ApiTenantFeatures>;
    }
  ) =>
    apiFetch<ApiOrganizationSettings>("/settings/organization", {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  getIdentitySettings: (token: string) =>
    apiFetch<ApiIdentitySettings>("/settings/identity", {}, token),

  updateIdentitySettings: (token: string, body: ApiIdentitySettingsUpdate) =>
    apiFetch<ApiIdentitySettings>("/settings/identity", {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  getGatewaySettings: (token: string) =>
    apiFetch<ApiGatewaySettings>("/settings/gateway", {}, token),

  updateGatewaySettings: (token: string, body: ApiGatewaySettingsUpdate) =>
    apiFetch<ApiGatewaySettings>("/settings/gateway", {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  getPublicTenantBranding: (tenantSlug: string) =>
    apiFetch<ApiPublicTenantBranding>(`/tenants/branding/${encodeURIComponent(tenantSlug)}`),

  resolvePublicSite: (params: { host?: string; subdomain?: string; slug?: string }) => {
    const query = new URLSearchParams();
    if (params.host) query.set("host", params.host);
    if (params.subdomain) query.set("subdomain", params.subdomain);
    if (params.slug) query.set("slug", params.slug);
    const qs = query.toString();
    return apiFetch<ApiPublicSiteConfig>(`/tenants/site-config${qs ? `?${qs}` : ""}`);
  },

  listPublicOidcProviders: (tenantSlug: string) =>
    apiFetch<ApiPublicOidcProvider[]>(`/auth/oidc/providers?tenant_slug=${encodeURIComponent(tenantSlug)}`),

  startOidcLogin: (tenantSlug: string, providerId: string) =>
    apiFetch<ApiOidcAuthorizeResponse>(
      `/auth/oidc/authorize?tenant_slug=${encodeURIComponent(tenantSlug)}&provider_id=${encodeURIComponent(providerId)}`
    ),

  completeOidcLogin: (body: { code: string; state: string }) =>
    apiFetch<ApiTokenResponse>("/auth/oidc/callback", { method: "POST", body: JSON.stringify(body) }),

  getPlatformConfig: () => apiFetch<ApiPlatformConfig>("/platform/config"),

  listPlatformTenants: (token: string) =>
    apiFetch<ApiPlatformTenant[]>("/platform/tenants", {}, token),

  createPlatformTenant: (token: string, body: ApiPlatformTenantCreateRequest) =>
    apiFetch<ApiPlatformTenantProvisionResult>("/platform/tenants", {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  updatePlatformTenant: (token: string, tenantId: string, body: ApiPlatformTenantUpdateRequest) =>
    apiFetch<ApiPlatformTenant>(`/platform/tenants/${tenantId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }, token),

  getPlatformOpsOverview: (token: string) =>
    apiFetch<ApiPlatformOpsOverview>("/platform/ops/overview", {}, token),

  getPlatformUsageOverview: (token: string, days = 30) =>
    apiFetch<ApiPlatformUsageOverview>(`/platform/usage/overview?days=${days}`, {}, token),

  createPlatformTenantInvite: (
    token: string,
    tenantId: string,
    body: { email: string; role?: string; admin_name?: string; template_slug?: string; send_email?: boolean }
  ) =>
    apiFetch<ApiPlatformTenantInvite>(`/platform/tenants/${tenantId}/invites`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  listInviteEmailTemplates: (token: string) =>
    apiFetch<ApiInviteEmailTemplate[]>("/platform/invite-email/templates", {}, token),

  updateInviteEmailTemplate: (
    token: string,
    slug: string,
    body: { subject: string; html_body: string; text_body?: string }
  ) =>
    apiFetch<ApiInviteEmailTemplate>(`/platform/invite-email/templates/${slug}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  resetInviteEmailTemplate: (token: string, slug: string) =>
    apiFetch<ApiInviteEmailTemplate>(`/platform/invite-email/templates/${slug}/reset`, {
      method: "POST",
    }, token),

  previewInviteEmail: (
    token: string,
    body: {
      template_slug: string;
      tenant_name?: string;
      admin_name?: string;
      admin_email?: string;
      invite_url?: string;
      expires_at?: string;
      tenant_url?: string;
    }
  ) =>
    apiFetch<ApiInviteEmailPreview>("/platform/invite-email/preview", {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  previewInvite: (inviteToken: string) =>
    apiFetch<ApiInvitePreview>(`/auth/invite/${encodeURIComponent(inviteToken)}`),

  acceptInvite: (body: { token: string; password: string; name?: string }) =>
    apiFetch<ApiAcceptInviteResult>("/auth/accept-invite", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listOidcProviders: (token: string) =>
    apiFetch<ApiOidcProvider[]>("/settings/oidc", {}, token),

  createOidcProvider: (token: string, body: ApiOidcProviderCreateRequest) =>
    apiFetch<ApiOidcProvider>("/settings/oidc", { method: "POST", body: JSON.stringify(body) }, token),

  updateOidcProvider: (token: string, providerId: string, body: ApiOidcProviderUpdateRequest) =>
    apiFetch<ApiOidcProvider>(`/settings/oidc/${providerId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  deleteOidcProvider: (token: string, providerId: string) =>
    apiFetch<void>(`/settings/oidc/${providerId}`, { method: "DELETE" }, token),

  listUagMappings: (token: string) => apiFetch<ApiUagMapping[]>("/uag/mappings", {}, token),

  createUagMapping: (
    token: string,
    body: {
      requested_model: string;
      actual_model: string;
      target_provider: string;
      emulate_protocol?: string;
      enabled?: boolean;
    }
  ) => apiFetch<ApiUagMapping>("/uag/mappings", { method: "POST", body: JSON.stringify(body) }, token),

  updateUagMapping: (
    token: string,
    mappingId: string,
    body: {
      requested_model?: string;
      actual_model?: string;
      target_provider?: string;
      emulate_protocol?: string;
      enabled?: boolean;
    }
  ) =>
    apiFetch<ApiUagMapping>(`/uag/mappings/${mappingId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  deleteUagMapping: (token: string, mappingId: string) =>
    apiFetch<void>(`/uag/mappings/${mappingId}`, { method: "DELETE" }, token),

  getUagStats: (token: string) => apiFetch<ApiUagStats>("/uag/stats", {}, token),

  getUagSettings: (token: string) => apiFetch<ApiUagSettings>("/uag/settings", {}, token),

  updateUagSettings: (token: string, body: { client_response_protocol?: string }) =>
    apiFetch<ApiUagSettings>("/uag/settings", { method: "PUT", body: JSON.stringify(body) }, token),

  simulateUagTranslation: (
    token: string,
    body: { model: string; messages: { role: string; content: string }[]; routing_context?: Record<string, unknown> }
  ) => apiFetch<ApiUagSimulateResult>("/uag/simulate", { method: "POST", body: JSON.stringify(body) }, token),

  listUagPolicies: (token: string) => apiFetch<ApiUagPolicy[]>("/uag/policies", {}, token),

  createUagPolicy: (
    token: string,
    body: {
      name: string;
      conditions: Record<string, string>;
      actions: Record<string, string>;
      priority?: number;
      enabled?: boolean;
    }
  ) => apiFetch<ApiUagPolicy>("/uag/policies", { method: "POST", body: JSON.stringify(body) }, token),

  updateUagPolicy: (
    token: string,
    policyId: string,
    body: {
      name?: string;
      conditions?: Record<string, string>;
      actions?: Record<string, string>;
      priority?: number;
      enabled?: boolean;
    }
  ) =>
    apiFetch<ApiUagPolicy>(`/uag/policies/${policyId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  deleteUagPolicy: (token: string, policyId: string) =>
    apiFetch<void>(`/uag/policies/${policyId}`, { method: "DELETE" }, token),

  getVaultStatus: (token: string) =>
    apiFetch<ApiVaultStatus>("/security/vault/status", {}, token),

  listUsers: (token: string) =>
    apiFetch<ApiTenantUser[]>("/users", {}, token),

  createUser: (token: string, body: ApiTenantUserCreate) =>
    apiFetch<ApiTenantUser>("/users", { method: "POST", body: JSON.stringify(body) }, token),

  updateUser: (token: string, userId: string, body: ApiTenantUserUpdate) =>
    apiFetch<ApiTenantUser>(`/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }, token),

  getRbacPermissions: (token: string) =>
    apiFetch<ApiRbacPermissions>("/rbac/permissions", {}, token),

  getRbacMatrix: (token: string) =>
    apiFetch<ApiRbacMatrix>("/rbac/matrix", {}, token),

  getDashboardMetrics: (token: string) =>
    apiFetch<ApiDashboardMetrics>("/dashboard/metrics", {}, token),

  getDashboardOverview: (token: string) =>
    apiFetch<ApiDashboardOverview>("/dashboard/overview", {}, token),

  getCostAnalytics: (token: string, days = 30) =>
    apiFetch<ApiCostAnalytics>(`/dashboard/cost-analytics?days=${days}`, {}, token),

  getDashboardMetricInsight: (
    token: string,
    metricKey: string,
    context?: ApiMetricInsightContext
  ) =>
    apiFetch<ApiDashboardMetricInsight>(
      `/dashboard/metrics/${metricKey}/insights`,
      context
        ? {
            method: "POST",
            body: JSON.stringify(context),
          }
        : {},
      token
    ),

  getNotifications: (token: string, readIds: string[] = [], limit = 30) => {
    const query = new URLSearchParams({ limit: String(limit) });
    if (readIds.length > 0) query.set("read", readIds.join(","));
    return apiFetch<ApiNotificationListResponse>(`/notifications?${query.toString()}`, {}, token);
  },

  getMcpServers: (token: string) =>
    apiFetch<ApiMcpServer[]>("/mcp/servers", {}, token),

  getMcpSsoInjection: (token: string, serverId: string) =>
    apiFetch<ApiMcpSsoInjectionConfig>(`/mcp/servers/${serverId}/sso-injection`, {}, token),

  updateMcpSsoInjection: (token: string, serverId: string, body: ApiMcpSsoInjectionConfigRequest) =>
    apiFetch<ApiMcpSsoInjectionConfig>(`/mcp/servers/${serverId}/sso-injection`, {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  getMcpToolDenyLists: (token: string) =>
    apiFetch<ApiMcpToolDenyRule[]>("/rbac/tool-deny-lists", {}, token),

  createMcpToolDenyRule: (token: string, body: ApiMcpToolDenyRuleRequest) =>
    apiFetch<ApiMcpToolDenyRule>("/rbac/tool-deny-lists", {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  deleteMcpToolDenyRule: (token: string, ruleId: string) =>
    apiFetch<void>(`/rbac/tool-deny-lists/${ruleId}`, { method: "DELETE" }, token),

  createMcpServer: (token: string, body: ApiMcpServerCreateRequest) =>
    apiFetch<ApiMcpServer>("/mcp/servers", { method: "POST", body: JSON.stringify(body) }, token),

  updateMcpServer: (token: string, serverId: string, body: ApiMcpServerUpdateRequest) =>
    apiFetch<ApiMcpServer>(`/mcp/servers/${serverId}`, { method: "PUT", body: JSON.stringify(body) }, token),

  deleteMcpServer: (token: string, serverId: string) =>
    apiFetch<void>(`/mcp/servers/${serverId}`, { method: "DELETE" }, token),

  checkMcpServerHealth: (token: string, serverId: string) =>
    apiFetch<ApiMcpHealthCheckResponse>(`/mcp/servers/${serverId}/health-check`, { method: "POST" }, token),

  checkAllMcpServersHealth: (token: string) =>
    apiFetch<ApiMcpHealthCheckBatchResponse>("/mcp/servers/health-check-all", { method: "POST" }, token),

  discoverMcpServerTools: (token: string, serverId: string) =>
    apiFetch<ApiMcpDiscoverToolsResponse>(`/mcp/servers/${serverId}/discover-tools`, { method: "POST" }, token),

  invokeMcpServerTool: (token: string, serverId: string, body: ApiMcpToolInvokeRequest) =>
    apiFetch<ApiMcpToolInvokeResponse>(`/mcp/servers/${serverId}/tools/invoke`, { method: "POST", body: JSON.stringify(body) }, token),

  getDynamicToolSettings: (token: string) =>
    apiFetch<ApiDynamicToolSettings>("/mcp/dynamic-tools/settings", {}, token),

  updateDynamicToolSettings: (token: string, body: { enabled?: boolean; max_tools?: number }) =>
    apiFetch<ApiDynamicToolSettings>("/mcp/dynamic-tools/settings", {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  previewDynamicTools: (token: string, body: { query: string; max_tools?: number }) =>
    apiFetch<ApiDynamicToolPreview>("/mcp/dynamic-tools/preview", {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  getMcpMultiplexInfo: (token: string) =>
    apiFetch<ApiMcpMultiplexInfo>("/mcp/multiplex", {}, token),

  getMcpCatalog: (token: string) =>
    apiFetch<ApiMcpCatalogList>("/mcp/catalog", {}, token),

  installMcpCatalogEntry: (token: string, slug: string, body: ApiMcpCatalogInstallRequest = {}) =>
    apiFetch<ApiMcpServer>(`/mcp/catalog/${encodeURIComponent(slug)}/install`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  installCustomMcpServer: (token: string, body: ApiMcpCatalogCustomInstallRequest) =>
    apiFetch<ApiMcpServer>("/mcp/catalog/custom", {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  getMcpOAuthList: (token: string) =>
    apiFetch<ApiMcpOAuthList>("/mcp/oauth", {}, token),

  getMcpOAuth: (token: string, serverId: string) =>
    apiFetch<ApiMcpOAuthStatus>(`/mcp/servers/${serverId}/oauth`, {}, token),

  upsertMcpOAuth: (token: string, serverId: string, body: ApiMcpOAuthUpsertRequest) =>
    apiFetch<ApiMcpOAuthStatus>(`/mcp/servers/${serverId}/oauth`, {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  refreshMcpOAuth: (token: string, serverId: string) =>
    apiFetch<ApiMcpOAuthStatus>(`/mcp/servers/${serverId}/oauth/refresh`, { method: "POST" }, token),

  deleteMcpOAuth: (token: string, serverId: string) =>
    apiFetch<void>(`/mcp/servers/${serverId}/oauth`, { method: "DELETE" }, token),

  getMcpAgentSettings: (token: string) =>
    apiFetch<ApiMcpAgentSettings>("/mcp/agent-settings", {}, token),

  updateMcpAgentSettings: (token: string, toggles: Record<string, boolean>) =>
    apiFetch<ApiMcpAgentSettings>("/mcp/agent-settings", {
      method: "PUT",
      body: JSON.stringify({ toggles }),
    }, token),

  updateMcpServerAllowedAgents: (token: string, serverId: string, allowed_agents: string[]) =>
    apiFetch<ApiMcpAgentSettings>(`/mcp/servers/${serverId}/allowed-agents`, {
      method: "PUT",
      body: JSON.stringify({ allowed_agents }),
    }, token),

  detectMcpAgent: (token: string, body: { user_agent?: string; metadata?: Record<string, unknown> }) =>
    apiFetch<ApiMcpAgentDetect>("/mcp/agents/detect", {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  getMcpPortal: (token: string) =>
    apiFetch<ApiMcpPortalList>("/mcp/portal", {}, token),

  getMcpPortalSettings: (token: string) =>
    apiFetch<ApiMcpPortalSettings>("/mcp/portal/settings", {}, token),

  updateMcpPortalSettings: (token: string, enabled: boolean) =>
    apiFetch<ApiMcpPortalSettings>("/mcp/portal/settings", {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    }, token),

  updateMcpServerPortalVisibility: (token: string, serverId: string, portal_visible: boolean) =>
    apiFetch<ApiMcpServer>(`/mcp/servers/${serverId}/portal-visibility`, {
      method: "PUT",
      body: JSON.stringify({ portal_visible }),
    }, token),

  connectMcpPortalServer: (token: string, serverId: string, access_token: string) =>
    apiFetch<ApiMcpPortalConnect>(`/mcp/portal/${serverId}/connect`, {
      method: "POST",
      body: JSON.stringify({ access_token }),
    }, token),

  disconnectMcpPortalServer: (token: string, serverId: string) =>
    apiFetch<void>(`/mcp/portal/${serverId}/connect`, { method: "DELETE" }, token),

  getMcpUrlFilters: (token: string) =>
    apiFetch<ApiMcpUrlFilterSettings>("/mcp/url-filters", {}, token),

  updateMcpUrlFilters: (token: string, body: ApiMcpUrlFilterSettingsUpdate) =>
    apiFetch<ApiMcpUrlFilterSettings>("/mcp/url-filters", {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  probeMcpUrlFilter: (token: string, url: string) =>
    apiFetch<ApiMcpUrlFilterProbe>("/mcp/url-filters/probe", {
      method: "POST",
      body: JSON.stringify({ url }),
    }, token),

  getMcpToolRisk: (token: string) =>
    apiFetch<ApiMcpToolRiskInventory>("/mcp/tool-risk", {}, token),

  updateMcpToolRiskSettings: (token: string, body: { auto_hide_destructive: boolean }) =>
    apiFetch<ApiMcpToolRiskInventory>("/mcp/tool-risk/settings", {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  updateMcpServerToolRisk: (
    token: string,
    serverId: string,
    body: { tools: Array<{ name: string; risk?: string | null; hidden?: boolean | null }> },
  ) =>
    apiFetch<ApiMcpToolRiskInventory>(`/mcp/servers/${serverId}/tool-risk`, {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  getAuditLogs: (token: string, params?: { search?: string; status?: string; since?: string; limit?: number; from_date?: string; to_date?: string; audit_id?: string }) => {
    const query = new URLSearchParams();
    if (params?.search) query.set("search", params.search);
    if (params?.audit_id) query.set("audit_id", params.audit_id);
    if (params?.status) query.set("status", params.status);
    if (params?.since) query.set("since", params.since);
    if (params?.limit) query.set("limit", String(params.limit));
    appendDateRange(query, params);
    const qs = query.toString();
    return apiFetch<ApiAuditLog[]>(`/audit/logs${qs ? `?${qs}` : ""}`, {}, token);
  },

  getAuditLogBody: (token: string, auditId: string) =>
    apiFetch<ApiAuditLogBody>(`/audit/logs/${auditId}/body`, {}, token),

  getRequestLogSettings: (token: string) =>
    apiFetch<ApiRequestLogSettings>("/audit/request-log-settings", {}, token),

  updateRequestLogSettings: (token: string, retentionDays: number) =>
    apiFetch<ApiRequestLogSettings>(
      "/audit/request-log-settings",
      { method: "PUT", body: JSON.stringify({ retention_days: retentionDays }) },
      token,
    ),

  purgeRequestLogs: (token: string) =>
    apiFetch<{ purged: number; stored_entries: number }>("/audit/purge-request-logs", { method: "POST" }, token),

  getAuditIngestSources: (token: string, days = 7) =>
    apiFetch<ApiAuditIngestSource[]>(`/audit/ingest/sources?days=${days}`, {}, token),

  ingestAuditLogs: (
    token: string,
    events: ApiAuditIngestEvent[]
  ) =>
    apiFetch<ApiAuditIngestResult>("/audit/ingest", { method: "POST", body: JSON.stringify({ events }) }, token),

  downloadAuditExport: async (token: string, format: "json" | "ndjson" | "cef" = "json"): Promise<Blob> => {
    const response = await fetch(`${API_BASE}/audit/export?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      const text = await response.text().catch(() => response.statusText);
      throw new ApiError(text || `Export failed (${response.status})`, response.status);
    }
    return response.blob();
  },

  listSiemConnectors: (token: string) =>
    apiFetch<ApiSiemConnector[]>("/audit/siem/connectors", {}, token),

  createSiemConnector: (token: string, body: ApiSiemConnectorCreateRequest) =>
    apiFetch<ApiSiemConnector>("/audit/siem/connectors", { method: "POST", body: JSON.stringify(body) }, token),

  deleteSiemConnector: (token: string, connectorId: string) =>
    apiFetch<void>(`/audit/siem/connectors/${connectorId}`, { method: "DELETE" }, token),

  pushSiemConnector: (token: string, connectorId: string) =>
    apiFetch<ApiSiemExportResult>(`/audit/siem/connectors/${connectorId}/push`, { method: "POST" }, token),

  queueSiemExportAll: (token: string) =>
    apiFetch<{ job_id: string; message: string }>("/audit/siem/export-all", { method: "POST" }, token),

  getPolicyTree: (token: string) =>
    apiFetch<ApiPolicyTreeNode[]>("/policies/tree", {}, token),

  createPolicy: (token: string, body: ApiPolicyCreateRequest) =>
    apiFetch<ApiPolicyTreeNode>("/policies", { method: "POST", body: JSON.stringify(body) }, token),

  updatePolicy: (token: string, policyId: string, body: ApiPolicyUpdateRequest) =>
    apiFetch<ApiPolicyTreeNode>(`/policies/${policyId}`, { method: "PUT", body: JSON.stringify(body) }, token),

  seedStarterPolicyRules: (token: string, policyId?: string) => {
    const query = policyId ? `?policy_id=${encodeURIComponent(policyId)}` : "";
    return apiFetch<{ policies_updated: number; message: string }>(
      `/policies/seed-starter-rules${query}`,
      { method: "POST" },
      token,
    );
  },

  seedComplianceTemplate: (token: string, templateId: string) =>
    apiFetch<{ message: string }>(
      "/policies/seed-compliance-template",
      { method: "POST", body: JSON.stringify({ template_id: templateId }) },
      token,
    ),

  getPolicyRules: (token: string, policyId?: string) => {
    const query = policyId ? `?policy_id=${encodeURIComponent(policyId)}` : "";
    return apiFetch<ApiPolicyRule[]>(`/policies/rules${query}`, {}, token);
  },

  savePolicyRules: (token: string, policyId: string, body: ApiPolicyRulesSaveRequest) =>
    apiFetch<ApiPolicyRule[]>(`/policies/${policyId}/rules`, { method: "PUT", body: JSON.stringify(body) }, token),

  testPolicyRules: (token: string, body: ApiPolicyTestRequest) =>
    apiFetch<ApiPolicyTestResponse>("/policies/test", { method: "POST", body: JSON.stringify(body) }, token),

  getPolicyConditionHelp: (token: string) =>
    apiFetch<ApiPolicyConditionHelpExample[]>("/policies/condition-help", {}, token),

  assistPolicyBuilding: (token: string, body: ApiPolicyAssistRequest) =>
    apiFetch<ApiPolicyAssistResponse>("/policies/assist", { method: "POST", body: JSON.stringify(body) }, token),

  assistCustomIntentBuilding: (token: string, goal: string) =>
    apiFetch<ApiCustomIntentAssistResponse>("/governance/custom-intents/assist", { method: "POST", body: JSON.stringify({ goal }) }, token),


  getPolicyGraphLinks: (token: string, nodeId?: string) => {
    const query = nodeId ? `?node_id=${encodeURIComponent(nodeId)}` : "";
    return apiFetch<ApiPolicyGraphLink[]>(`/policies/graph-links${query}`, {}, token);
  },

  getIngressBindings: (token: string) =>
    apiFetch<ApiIngressBinding[]>("/governance/ingress-bindings", {}, token),

  getDataProtectionOverview: (token: string) =>
    apiFetch<ApiDataProtectionOverview>("/data-protection/overview", {}, token),

  getSecurityOverview: (token: string) =>
    apiFetch<ApiSecurityOverview>("/security/overview", {}, token),

  scanSecurityContent: (token: string, body: { content: string }) =>
    apiFetch<ApiSecurityScanResponse>("/security/scan", { method: "POST", body: JSON.stringify(body) }, token),

  getOpaStatus: (token: string) =>
    apiFetch<ApiOpaStatus>("/security/opa/status", {}, token),

  evaluateAbacPolicy: (token: string, body: ApiAbacEvaluateRequest) =>
    apiFetch<ApiAbacEvaluateResponse>("/security/opa/evaluate", { method: "POST", body: JSON.stringify(body) }, token),

  getComplianceFrameworks: (token: string) =>
    apiFetch<ApiDashboardOverview["compliance_frameworks"]>("/compliance/frameworks", {}, token),

  listComplianceSnapshots: (token: string) =>
    apiFetch<ApiComplianceSnapshotSummary[]>("/compliance/snapshots", {}, token),

  createComplianceSnapshot: (token: string, body: { notes?: string }) =>
    apiFetch<ApiComplianceSnapshotDetail>("/compliance/snapshots", { method: "POST", body: JSON.stringify(body) }, token),

  getComplianceSnapshot: (token: string, snapshotId: string) =>
    apiFetch<ApiComplianceSnapshotDetail>(`/compliance/snapshots/${snapshotId}`, {}, token),

  listGenaiEvidenceBundles: (token: string) =>
    apiFetch<ApiGenaiEvidenceSummary[]>("/rag-gateway/evidence", {}, token),

  getRagGatewaySettings: (token: string) =>
    apiFetch<ApiRagGatewaySettings>("/rag-gateway/settings", {}, token),

  updateRagGatewaySettings: (
    token: string,
    body: {
      pinecone_enabled?: boolean;
      pinecone_api_key?: string;
      pinecone_host?: string;
      pinecone_namespace?: string;
      pinecone_dimension?: number;
    }
  ) =>
    apiFetch<ApiRagGatewaySettings>("/rag-gateway/settings", {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  evaluateRagMovement: (
    token: string,
    body: {
      content: string;
      destination?: string;
      operation?: string;
      policy_bundle?: string;
      region?: string;
      exemption_id?: string;
    }
  ) =>
    apiFetch<ApiRagMovementResponse>("/rag-gateway/evaluate", {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  ingestRagContent: (
    token: string,
    body: {
      content: string;
      destination?: string;
      policy_bundle?: string;
      region?: string;
      namespace?: string;
      document_id?: string;
      exemption_id?: string;
    }
  ) =>
    apiFetch<ApiRagIngestResponse>("/rag-gateway/ingest", {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  scanIacEvidence: (token: string) =>
    apiFetch<ApiIacEvidenceReport>("/rag-gateway/iac-evidence", {}, token),

  createDemoRagEvents: (token: string) =>
    apiFetch<{ seeded: boolean; evidence_count: number; message: string }>(
      "/rag-gateway/demo-events",
      { method: "POST" },
      token
    ),

  listPolicyExemptions: (token: string) =>
    apiFetch<ApiPolicyExemption[]>("/rag-gateway/exemptions", {}, token),

  createPolicyExemption: (
    token: string,
    body: {
      reason: string;
      ticket_ref?: string;
      duration_minutes?: number;
      max_uses?: number;
      allowed_destinations?: ("llm" | "embedding")[];
    }
  ) =>
    apiFetch<ApiPolicyExemption>("/rag-gateway/exemptions", {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  revokePolicyExemption: (token: string, exemptionId: string) =>
    apiFetch<ApiPolicyExemption>(`/rag-gateway/exemptions/${exemptionId}`, {
      method: "DELETE",
    }, token),

  reevaluateComplianceFramework: (token: string, frameworkKey: string) =>
    apiFetch<ApiComplianceReevaluateResponse>(
      `/compliance/frameworks/${encodeURIComponent(frameworkKey)}/reevaluate`,
      { method: "POST" },
      token
    ),

  generateComplianceRemediation: (
    token: string,
    body: { framework_name: string; control_id: string; mode: "manual" | "ai" }
  ) =>
    apiFetch<ApiComplianceRemediationResponse>("/compliance/remediation", {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  getLlmProviders: (token: string) =>
    apiFetch<ApiRoutingModel[]>("/llm/providers", {}, token),

  createLlmProvider: (token: string, body: ApiLlmProviderCreateRequest) =>
    apiFetch<ApiRoutingModel>("/llm/providers", { method: "POST", body: JSON.stringify(body) }, token),

  updateLlmProvider: (token: string, providerId: string, body: ApiLlmProviderUpdateRequest) =>
    apiFetch<ApiRoutingModel>(`/llm/providers/${providerId}`, { method: "PUT", body: JSON.stringify(body) }, token),

  deleteLlmProvider: (token: string, providerId: string) =>
    apiFetch<void>(`/llm/providers/${providerId}`, { method: "DELETE" }, token),

  rebalanceLlmProviders: (token: string) =>
    apiFetch<ApiProviderRebalanceResponse>("/llm/providers/rebalance-percentages", { method: "POST" }, token),

  getRoutingRules: (token: string) =>
    apiFetch<ApiRoutingRule[]>("/llm/routing-rules", {}, token),

  createRoutingRule: (token: string, body: ApiRoutingRuleCreateRequest) =>
    apiFetch<ApiRoutingRule>("/llm/routing-rules", { method: "POST", body: JSON.stringify(body) }, token),

  updateRoutingRule: (token: string, ruleId: string, body: ApiRoutingRuleUpdateRequest) =>
    apiFetch<ApiRoutingRule>(`/llm/routing-rules/${ruleId}`, { method: "PUT", body: JSON.stringify(body) }, token),

  deleteRoutingRule: (token: string, ruleId: string) =>
    apiFetch<void>(`/llm/routing-rules/${ruleId}`, { method: "DELETE" }, token),

  // BL-088: per-rule client API key assignment
  getRoutingRuleClientKeys: (token: string, ruleId: string) =>
    apiFetch<ApiClientApiKey[]>(`/llm/routing-rules/${ruleId}/client-keys`, {}, token),

  assignRoutingRuleClientKey: (token: string, ruleId: string, keyId: string) =>
    apiFetch<ApiClientApiKey[]>(`/llm/routing-rules/${ruleId}/client-keys/${keyId}`, { method: "POST" }, token),

  unassignRoutingRuleClientKey: (token: string, ruleId: string, keyId: string) =>
    apiFetch<ApiClientApiKey[]>(`/llm/routing-rules/${ruleId}/client-keys/${keyId}`, { method: "DELETE" }, token),

  getRoutingGroups: (token: string) =>
    apiFetch<ApiRoutingGroup[]>("/routing-groups", {}, token),

  createRoutingGroup: (token: string, body: ApiRoutingGroupCreateRequest) =>
    apiFetch<ApiRoutingGroup>("/routing-groups", { method: "POST", body: JSON.stringify(body) }, token),

  updateRoutingGroup: (token: string, groupId: string, body: ApiRoutingGroupUpdateRequest) =>
    apiFetch<ApiRoutingGroup>(`/routing-groups/${groupId}`, { method: "PUT", body: JSON.stringify(body) }, token),

  deleteRoutingGroup: (token: string, groupId: string) =>
    apiFetch<void>(`/routing-groups/${groupId}`, { method: "DELETE" }, token),

  getGatewayStatus: (token: string) =>
    apiFetch<ApiGatewayStatus>("/gateway/status", {}, token),

  getPolicyBundles: (token: string) =>
    apiFetch<ApiPolicyBundle[]>("/policy-bundles", {}, token),

  createPolicyBundle: (token: string, body: ApiPolicyBundleCreateRequest) =>
    apiFetch<ApiPolicyBundle>("/policy-bundles", { method: "POST", body: JSON.stringify(body) }, token),

  updatePolicyBundle: (token: string, bundleId: string, body: ApiPolicyBundleUpdateRequest) =>
    apiFetch<ApiPolicyBundle>(`/policy-bundles/${bundleId}`, { method: "PUT", body: JSON.stringify(body) }, token),

  deletePolicyBundle: (token: string, bundleId: string) =>
    apiFetch<void>(`/policy-bundles/${bundleId}`, { method: "DELETE" }, token),

  getClientApiKeys: (token: string) =>
    apiFetch<ApiClientApiKey[]>("/client-api-keys", {}, token),

  createClientApiKey: (token: string, body: ApiClientApiKeyCreateRequest) =>
    apiFetch<ApiClientApiKeyCreateResponse>("/client-api-keys", { method: "POST", body: JSON.stringify(body) }, token),

  updateClientApiKey: (token: string, keyId: string, body: ApiClientApiKeyUpdateRequest) =>
    apiFetch<ApiClientApiKey>(`/client-api-keys/${keyId}`, { method: "PUT", body: JSON.stringify(body) }, token),

  deleteClientApiKey: (token: string, keyId: string) =>
    apiFetch<void>(`/client-api-keys/${keyId}`, { method: "DELETE" }, token),

  chatCompletion: (
    token: string,
    body: {
      model?: string;
      messages: { role: string; content: string }[];
      stream?: boolean;
      routing_context?: Record<string, unknown>;
      debug?: boolean;
    }
  ) =>
    apiFetch<ChatCompletionResponse>(
      `/chat/completions${body.debug ? "?mode=debug" : ""}`,
      {
        method: "POST",
        body: JSON.stringify({
          model: body.model ?? "llama3.2",
          messages: body.messages,
          stream: body.stream ?? false,
          ...(body.routing_context ? { routing_context: body.routing_context } : {}),
        }),
      },
      token
    ),

  chatCompletionStream: async (
    token: string,
    body: {
      model?: string;
      messages: { role: string; content: string }[];
      routing_context?: Record<string, unknown>;
    },
    onChunk: (text: string) => void
  ): Promise<void> => {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };
    const response = await fetch(`${API_BASE}/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: body.model ?? "llama3.2",
        messages: body.messages,
        stream: true,
        ...(body.routing_context ? { routing_context: body.routing_context } : {}),
      }),
    });
    if (!response.ok) {
      const text = await response.text().catch(() => response.statusText);
      if (response.status === 401) {
        handleSessionExpired();
        throw new ApiError("Session expired. Please sign in again.", 401);
      }
      let message = text;
      try {
        const json = JSON.parse(text) as { detail?: string };
        message = json.detail ?? text;
      } catch {
        // keep raw text
      }
      throw new ApiError(message || `Stream failed (${response.status})`, response.status);
    }
    const reader = response.body?.getReader();
    if (!reader) throw new ApiError("No response body", 500);
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") return;
        try {
          const event = JSON.parse(raw) as {
            choices?: { delta?: { content?: string } }[];
            error?: { message?: string };
          };
          if (event.error?.message) throw new ApiError(event.error.message, 502);
          const content = event.choices?.[0]?.delta?.content;
          if (content) onChunk(content);
        } catch (err) {
          if (err instanceof ApiError) throw err;
        }
      }
    }
  },

  getOllamaStatus: (token: string) =>
    apiFetch<{
      enabled: boolean;
      reachable: boolean;
      base_url: string;
      models: string[];
      default_model: string;
      error?: string;
    }>("/gateway/ollama/status", {}, token),

  getObservabilityOverview: (token: string, params?: ApiDateRangeParams) => {
    const query = new URLSearchParams();
    appendDateRange(query, params);
    const qs = query.toString();
    return apiFetch<ApiObservabilityOverview>(`/observability/overview${qs ? `?${qs}` : ""}`, {}, token);
  },

  getObservabilityTraces: (token: string, limit = 20, params?: ApiDateRangeParams) => {
    const query = new URLSearchParams({ limit: String(limit) });
    appendDateRange(query, params);
    return apiFetch<ApiTraceSummary[]>(`/observability/traces?${query.toString()}`, {}, token);
  },

  getObservabilityTraceDetail: (token: string, auditId: string) =>
    apiFetch<ApiTraceSummary>(`/observability/traces/${auditId}`, {}, token),

  getTelemetryOperations: (token: string, params?: ApiDateRangeParams) => {
    const query = new URLSearchParams();
    appendDateRange(query, params);
    const qs = query.toString();
    return apiFetch<ApiTelemetryOperations>(`/telemetry/operations${qs ? `?${qs}` : ""}`, {}, token);
  },

  getTelemetrySla: (token: string, params?: ApiDateRangeParams) => {
    const query = new URLSearchParams();
    appendDateRange(query, params);
    const qs = query.toString();
    return apiFetch<ApiGatewaySla>(`/telemetry/sla${qs ? `?${qs}` : ""}`, {}, token);
  },

  getTelemetrySummary: (token: string, params?: ApiDateRangeParams) => {
    const query = new URLSearchParams();
    appendDateRange(query, params);
    const qs = query.toString();
    return apiFetch<ApiTelemetrySummary>(`/telemetry/summary${qs ? `?${qs}` : ""}`, {}, token);
  },

  getIntegrations: (token: string) =>
    apiFetch<ApiIntegrationSettings>("/settings/integrations", {}, token),

  updateIntegrations: (
    token: string,
    body: {
      openai_api_key?: string;
      gemini_api_key?: string;
      gemini_default_model?: string;
      ollama_enabled?: boolean;
      ollama_base_url?: string;
      ollama_default_model?: string;
    }
  ) =>
    apiFetch<ApiIntegrationSettings>("/settings/integrations", {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  getAiAssistSettings: (token: string) =>
    apiFetch<ApiAiAssistSettings>("/settings/ai-assist", {}, token),

  updateAiAssistSettings: (
    token: string,
    body: {
      enabled?: boolean;
      provider?: "openai" | "gemini" | "groq" | "ollama" | "vllm" | "custom";
      model?: string;
      api_key?: string;
      base_url?: string;
    },
  ) =>
    apiFetch<ApiAiAssistSettings>("/settings/ai-assist", {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  listAlertWebhooks: (token: string) =>
    apiFetch<ApiAlertWebhook[]>("/settings/alert-webhooks", {}, token),

  createAlertWebhook: (token: string, body: ApiAlertWebhookCreateRequest) =>
    apiFetch<ApiAlertWebhook>("/settings/alert-webhooks", { method: "POST", body: JSON.stringify(body) }, token),

  deleteAlertWebhook: (token: string, webhookId: string) =>
    apiFetch<void>(`/settings/alert-webhooks/${webhookId}`, { method: "DELETE" }, token),

  testAlertWebhook: (token: string, webhookId: string) =>
    apiFetch<ApiAlertWebhookTestResult>(`/settings/alert-webhooks/${webhookId}/test`, { method: "POST" }, token),

  getExecutiveSummary: (token: string, params?: ApiDateRangeParams) => {
    const query = new URLSearchParams();
    appendDateRange(query, params);
    const qs = query.toString();
    return apiFetch<ApiExecutiveSummary>(`/reports/executive-summary${qs ? `?${qs}` : ""}`, {}, token);
  },

  getReportCatalog: (token: string) =>
    apiFetch<ApiReportCatalogResponse>("/reports/catalog", {}, token),

  getReportQueryTemplates: (token: string) =>
    apiFetch<ApiReportQueryTemplatesResponse>("/reports/query-templates", {}, token),

  getReportDeliveryRecipients: (token: string) =>
    apiFetch<ApiReportDeliveryRecipientsResponse>("/reports/delivery-recipients", {}, token),

  createReport: (token: string, body: ApiReportCreateRequest) =>
    apiFetch<ApiReportCatalogEntry>("/reports", { method: "POST", body: JSON.stringify(body) }, token),

  updateReport: (token: string, reportId: string, body: ApiReportUpdateRequest) =>
    apiFetch<ApiReportCatalogEntry>(`/reports/${reportId}`, { method: "PUT", body: JSON.stringify(body) }, token),

  deleteReport: (token: string, reportId: string) =>
    apiFetch<void>(`/reports/${reportId}`, { method: "DELETE" }, token),

  previewReportQuery: (token: string, query: ApiReportQuery) =>
    apiFetch<ApiReportPreviewResponse>("/reports/preview", { method: "POST", body: JSON.stringify({ query }) }, token),

  previewReport: (token: string, reportId: string) =>
    apiFetch<ApiReportPreviewResponse>(`/reports/${reportId}/preview`, { method: "POST" }, token),

  getReportRunResult: (token: string, reportId: string) =>
    apiFetch<ApiReportRunResponse>(`/reports/${reportId}/run`, {}, token),

  runReport: async (token: string, reportId: string): Promise<ApiReportRunResponse> => {
    await apiFetch<{ report_id: string; status: string }>(
      `/reports/${reportId}/run`,
      { method: "POST" },
      token
    );

    for (let attempt = 0; attempt < 120; attempt++) {
      const response = await fetch(`${API_BASE}/reports/${reportId}/run`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 200) {
        return response.json() as Promise<ApiReportRunResponse>;
      }

      if (response.status === 202) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        continue;
      }

      const text = await response.text().catch(() => response.statusText);
      let message = text;
      try {
        const json = JSON.parse(text) as { detail?: string };
        message = json.detail ?? text;
      } catch {
        // keep raw text
      }
      if (response.status === 401) {
        handleSessionExpired();
        throw new ApiError("Session expired. Please sign in again.", 401);
      }
      throw new ApiError(message || `Report run failed (${response.status})`, response.status);
    }

    throw new ApiError("Report generation timed out", 504);
  },

  getReportSchedulerStatus: (token: string) =>
    apiFetch<ApiReportSchedulerStatus>("/reports/scheduler/status", {}, token),

  runDueScheduledReports: (token: string) =>
    apiFetch<ApiReportSchedulerRunDueResponse>(
      "/reports/scheduler/run-due",
      { method: "POST" },
      token
    ),

  downloadReport: async (token: string, reportId: string): Promise<{ blob: Blob; filename: string }> => {
    for (let attempt = 0; attempt < 120; attempt++) {
      const response = await fetch(`${API_BASE}/reports/${reportId}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 200) {
        const blob = await response.blob();
        const disposition = response.headers.get("Content-Disposition") ?? "";
        const match = disposition.match(/filename="([^"]+)"/);
        const filename = match?.[1] ?? `pysetu-${reportId}.csv`;
        return { blob, filename };
      }

      if (response.status === 202) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        continue;
      }

      const text = await response.text().catch(() => response.statusText);
      let message = text;
      try {
        const json = JSON.parse(text) as { detail?: string };
        message = json.detail ?? text;
      } catch {
        // keep raw text
      }
      if (response.status === 401) {
        handleSessionExpired();
        throw new ApiError("Session expired. Please sign in again.", 401);
      }
      throw new ApiError(message || `Download failed (${response.status})`, response.status);
    }

    throw new ApiError("Report download timed out", 504);
  },

  getQAOverview: (token: string) =>
    apiFetch<ApiQAOverview>("/qa/overview", {}, token),

  getQACycles: (token: string) =>
    apiFetch<ApiQATestCycleSummary[]>("/qa/cycles", {}, token),

  createQACycle: (
    token: string,
    body: { name: string; import_baseline?: boolean; import_baseline_defects?: boolean }
  ) =>
    apiFetch<ApiQATestCycleDetail>("/qa/cycles", { method: "POST", body: JSON.stringify(body) }, token),

  getQACycle: (token: string, cycleId: string) =>
    apiFetch<ApiQATestCycleDetail>(`/qa/cycles/${cycleId}`, {}, token),

  updateQACycle: (
    token: string,
    cycleId: string,
    body: { status?: string; release_decision?: string; notes?: string }
  ) =>
    apiFetch<ApiQATestCycleSummary>(`/qa/cycles/${cycleId}`, { method: "PATCH", body: JSON.stringify(body) }, token),

  updateQATestCase: (token: string, caseId: string, body: { status: string; notes?: string }) =>
    apiFetch<ApiQATestCase>(`/qa/test-cases/${caseId}`, { method: "PATCH", body: JSON.stringify(body) }, token),

  getQADefects: (token: string, params?: { cycle_id?: string; status?: string }) => {
    const query = new URLSearchParams();
    if (params?.cycle_id) query.set("cycle_id", params.cycle_id);
    if (params?.status) query.set("status", params.status);
    const qs = query.toString();
    return apiFetch<ApiQADefect[]>(`/qa/defects${qs ? `?${qs}` : ""}`, {}, token);
  },

  createQADefect: (
    token: string,
    body: {
      defect_code: string;
      severity: string;
      module: string;
      title: string;
      description?: string;
      cycle_id?: string;
      linked_case_id?: string;
    }
  ) =>
    apiFetch<ApiQADefect>("/qa/defects", { method: "POST", body: JSON.stringify(body) }, token),

  updateQADefect: (
    token: string,
    defectId: string,
    body: { severity?: string; title?: string; description?: string; status?: string }
  ) =>
    apiFetch<ApiQADefect>(`/qa/defects/${defectId}`, { method: "PATCH", body: JSON.stringify(body) }, token),

  getNextDefectCode: (token: string) =>
    apiFetch<{ defect_code: string }>("/qa/next-defect-code", {}, token),

  runQAAutomatedTests: (token: string, cycleId: string, scope: "all" | "failed" = "all") =>
    apiFetch<ApiQAAutomatedRunResponse>(
      `/qa/cycles/${cycleId}/run-automated?scope=${scope}`,
      { method: "POST" },
      token
    ),

  fileQADefectFromCase: (token: string, caseId: string) =>
    apiFetch<ApiQAFileDefectResponse>(`/qa/test-cases/${caseId}/file-defect`, { method: "POST" }, token),
};

export interface ApiDynamicToolSettings {
  enabled: boolean;
  max_tools: number;
  catalog_count: number;
  catalog_tokens: number;
}

export interface ApiDynamicToolPreview {
  enabled: boolean;
  catalog_count: number;
  selected_count: number;
  selected_names: string[];
  original_tokens: number;
  compressed_tokens: number;
  tokens_saved: number;
  savings_pct: number;
}

export interface ApiMcpMultiplexInfo {
  url: string;
  api_url: string;
  auth: string;
  tool_namespace: string;
  server_count: number;
  tool_count: number;
  sample_tools: string[];
  instructions: string;
}

export interface ApiMcpCatalogEntry {
  slug: string;
  name: string;
  description: string;
  category: string;
  transport: string;
  default_endpoint: string | null;
  tool_names: string[];
  auth_required: boolean;
  vendor: string;
  installed: boolean;
}

export interface ApiMcpCatalogList {
  entries: ApiMcpCatalogEntry[];
}

export interface ApiMcpCatalogInstallRequest {
  endpoint_url?: string | null;
  name?: string | null;
}

export interface ApiMcpCatalogCustomInstallRequest {
  name: string;
  endpoint_url: string;
  transport?: string;
  category?: string;
}

export interface ApiMcpOAuthStatus {
  configured: boolean;
  enabled: boolean;
  grant_type: string;
  token_url: string;
  client_id: string;
  scopes: string;
  has_client_secret: boolean;
  has_refresh_token: boolean;
  has_access_token: boolean;
  token_expires_at: string | null;
  token_fresh: boolean;
  secrets_backend: string;
  server_id?: string;
  server_name?: string;
}

export interface ApiMcpOAuthList {
  servers: Array<ApiMcpOAuthStatus & { server_id: string; server_name: string }>;
  secrets_backend: string;
}

export interface ApiMcpOAuthUpsertRequest {
  enabled?: boolean;
  grant_type?: string;
  token_url?: string | null;
  client_id?: string | null;
  scopes?: string | null;
  client_secret?: string | null;
  refresh_token?: string | null;
  access_token?: string | null;
}

export interface ApiMcpToolRiskItem {
  server_id: string;
  server_name: string;
  name: string;
  description: string;
  risk: string;
  hidden: boolean;
  auto_hidden: boolean;
  visible: boolean;
}

export interface ApiMcpToolRiskInventory {
  auto_hide_destructive: boolean;
  tools: ApiMcpToolRiskItem[];
  visible_count: number;
  hidden_count: number;
}

export interface ApiMcpAgentItem {
  slug: string;
  label: string;
  enabled: boolean;
}

export interface ApiMcpAgentServerAccess {
  server_id: string;
  server_name: string;
  allowed_agents: string[];
}

export interface ApiMcpAgentSettings {
  agents: ApiMcpAgentItem[];
  servers: ApiMcpAgentServerAccess[];
}

export interface ApiMcpAgentDetect {
  agent: string;
  mcp_enabled: boolean;
  label: string;
}

export interface ApiMcpPortalEntry {
  server_id: string;
  name: string;
  category: string;
  status: string;
  tool_count: number;
  tool_names: string[];
  auth_required: boolean;
  connection_status: string;
  catalog_slug?: string | null;
  vendor?: string;
  description?: string;
  portal_visible: boolean;
}

export interface ApiMcpPortalList {
  enabled: boolean;
  multiplex_url: string;
  entries: ApiMcpPortalEntry[];
}

export interface ApiMcpPortalSettings {
  enabled: boolean;
}

export interface ApiMcpPortalConnect {
  server_id: string;
  connection_status: string;
  connected_at: string;
}

export interface ApiMcpUrlFilterSettings {
  enabled: boolean;
  mode: string;
  patterns: string[];
  block_private_ips: boolean;
  web_search_enabled: boolean;
  vendor: string;
  vendor_endpoint: string;
  vendor_configured?: boolean;
}

export interface ApiMcpUrlFilterSettingsUpdate extends Partial<ApiMcpUrlFilterSettings> {
  vendor_api_key?: string;
}

export interface ApiMcpUrlFilterProbe {
  url: string;
  host: string;
  allowed: boolean;
  mode: string;
  private_host: boolean;
}

export interface ApiMcpServer {
  id: string;
  name: string;
  category: string;
  success_rate: number;
  avg_latency: number;
  total_calls: number;
  status: string;
  tools: number;
  tool_names: string[];
  endpoint_url: string | null;
  transport: string;
  connection_config: {
    auth_header?: string;
    timeout_sec?: number;
    catalog_slug?: string;
    portal_visible?: boolean;
    allowed_agents?: string[];
    tool_schemas?: ApiMcpToolSchema[];
    mcp_session?: Record<string, unknown>;
  };
  trust_score: number;
  risk_score: number;
}

export interface ApiMcpSsoInjectionConfigRequest {
  enabled: boolean;
  header_name: string;
  header_format: string;
  claim_extract: string;
}

export interface ApiMcpSsoInjectionConfig extends ApiMcpSsoInjectionConfigRequest {
  server_id: string;
  updated_at: string;
}

export interface ApiMcpToolDenyRuleRequest {
  role: string;
  server_id: string;
  tool_name: string;
  reason: string;
}

export interface ApiMcpToolDenyRule extends ApiMcpToolDenyRuleRequest {
  id: string;
  server_name: string;
  created_at: string;
}

export interface ApiMcpServerCreateRequest {
  name: string;
  category: string;
  status?: string;
  tool_names?: string[];
  endpoint_url?: string | null;
  transport?: string;
  connection_config?: { auth_header?: string; timeout_sec?: number };
}

export interface ApiMcpServerUpdateRequest {
  name?: string;
  category?: string;
  status?: string;
  tool_names?: string[];
  endpoint_url?: string | null;
  transport?: string;
  connection_config?: { auth_header?: string; timeout_sec?: number };
}

export interface ApiMcpHealthCheckResponse {
  server_id: string;
  server_name: string;
  status: string;
  ok: boolean;
  latency_ms: number;
  message: string;
  http_status: number | null;
  skipped: boolean;
  checked_at: string;
}

export interface ApiMcpHealthCheckBatchResponse {
  results: ApiMcpHealthCheckResponse[];
  healthy: number;
  degraded: number;
  offline: number;
  skipped: number;
}

export interface ApiMcpToolSchema {
  name: string;
  description?: string | null;
  inputSchema?: Record<string, unknown> | null;
}

export interface ApiMcpDiscoverToolsResponse {
  server_id: string;
  server_name: string;
  ok: boolean;
  tool_names: string[];
  tools_count: number;
  tool_schemas?: ApiMcpToolSchema[];
  message: string;
  latency_ms: number;
  skipped: boolean;
  checked_at: string;
}

export interface ApiPolicyRulesSaveRequest {
  rules: ApiPolicyRule[];
}

export interface ApiNotification {
  id: string;
  title: string;
  message: string;
  severity: string;
  category: string;
  timestamp: string;
  action: string;
  resource: string;
  status: string;
}

export interface ApiNotificationListResponse {
  notifications: ApiNotification[];
  unread_count: number;
}

export interface ApiAuditLog {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource: string;
  status: string;
  risk: string;
  details: string;
  has_request_log?: boolean;
}

export interface ApiAuditLogBody {
  audit_log_id: string;
  request_payload: Record<string, unknown> | null;
  response_payload: Record<string, unknown> | null;
  guardrail_events: Record<string, unknown> | null;
  tool_events: Array<Record<string, unknown>> | null;
  created_at: string | null;
}

export interface ApiRequestLogSettings {
  retention_days: number;
  stored_entries: number;
}

export interface ApiAuditIngestSource {
  source: string;
  count: number;
}

export interface ApiAuditIngestEvent {
  actor: string;
  action: string;
  resource: string;
  status: "allowed" | "blocked" | "review";
  risk?: "low" | "medium" | "high" | "critical";
  details?: string;
  source?: string;
  external_id?: string;
  trace_id?: string;
}

export interface ApiAuditIngestResult {
  accepted: number;
  skipped: number;
  duplicates: number;
  ids: string[];
}

export interface ApiSiemConnector {
  id: string;
  name: string;
  connector_type: string;
  endpoint_url: string;
  export_format: string;
  enabled: boolean;
  events_exported: number;
  last_export_at: string | null;
  last_error: string;
  auth_token_set: boolean;
  auth_token_masked: string | null;
}

export interface ApiSiemConnectorCreateRequest {
  name: string;
  connector_type: string;
  endpoint_url: string;
  auth_token?: string;
  export_format?: string;
  enabled?: boolean;
}

export interface ApiSiemExportResult {
  exported: number;
  connector_id: string;
  connector_name: string;
  message: string;
}

export interface ApiAlertWebhook {
  id: string;
  name: string;
  webhook_type: string;
  endpoint_url: string;
  channel?: string | null;
  enabled: boolean;
  alerts_sent: number;
  last_alert_at: string | null;
  last_error: string;
  auth_token_set: boolean;
  auth_token_masked: string | null;
}

export interface ApiAlertWebhookCreateRequest {
  name: string;
  webhook_type: string;
  endpoint_url: string;
  auth_token?: string;
  channel?: string;
  enabled?: boolean;
}

export interface ApiAlertWebhookTestResult {
  webhook_id: string;
  webhook_name: string;
  message: string;
}

export interface ApiPolicyTreeNode {
  id: string;
  label: string;
  type: string;
  status?: string;
  children?: ApiPolicyTreeNode[];
}

export interface ApiPolicyCreateRequest {
  name: string;
  policy_type: "policy" | "folder";
  status?: "active" | "draft" | "disabled";
  parent_id?: string | null;
}

export interface ApiPolicyUpdateRequest {
  name?: string;
  status?: "active" | "draft" | "disabled";
}

export interface ApiPolicyRule {
  id: string;
  name: string;
  condition: string;
  action: string;
  severity: string;
  enabled: boolean;
}

export interface ApiPolicyTestRequest {
  content: string;
  rules: ApiPolicyRule[];
}

export interface ApiPolicyViolation {
  rule_name: string;
  action: string;
  severity: string;
  detail: string;
}

export interface ApiPolicyTestResponse {
  allowed: boolean;
  action: string;
  violations: ApiPolicyViolation[];
  redacted_content: string | null;
  risk: string;
}

export interface ApiPolicyConditionHelpExample {
  title: string;
  condition: string;
  description: string;
  action: string;
  severity: string;
}

export interface ApiPolicyRuleSuggestion {
  id: string;
  name: string;
  condition: string;
  action: string;
  severity: string;
  enabled: boolean;
  rationale: string;
}

export interface ApiPolicyAssistRequest {
  goal?: string;
  policy_name?: string | null;
  existing_rule_names?: string[];
}

export interface ApiPolicyAssistResponse {
  summary: string;
  suggestions: ApiPolicyRuleSuggestion[];
  condition_help: ApiPolicyConditionHelpExample[];
  ai_enhanced?: boolean;
  ai_assist_available?: boolean;
}

export interface ApiCustomIntentAssistSuggestion {
  name: string;
  description: string;
  action: string;
  keywords: string[];
  confidence_threshold: number;
}

export interface ApiCustomIntentAssistResponse {
  summary: string;
  ai_enhanced?: boolean;
  suggestions: ApiCustomIntentAssistSuggestion[];
}

export interface ApiPolicyGraphLink {
  policy_id: string;
  policy_name: string;
  policy_status: string | null;
  graph_node_id: string;
  graph_node_label: string;
  graph_node_type: string;
  edge_labels: string[];
  description: string;
}

export interface ApiIngressBindingPolicy {
  policy_id: string;
  policy_name: string;
  policy_status: string | null;
  graph_node_id: string;
  graph_node_label: string;
}

export interface ApiIngressBinding {
  id: string;
  name: string;
  bundle_id: string | null;
  bundle_name: string | null;
  is_default: boolean;
  graph_node_ids: string[];
  policies: ApiIngressBindingPolicy[];
}

export interface ApiDataProtectionOverview {
  classifications: { label: string; count: number; percentage: number; color: string }[];
  regions: {
    id: string;
    name: string;
    percentage: number;
    records: number;
    status: "compliant" | "review" | "at-risk";
    color: string;
    hubs: string[];
    policy: string;
  }[];
  total_scanned: number;
  pii_redactions: number;
  blocked_events: number;
}

export interface ApiSecurityThreatBreakdown {
  category: string;
  label: string;
  count: number;
  percentage: number;
}

export interface ApiSecurityDetectionItem {
  id: string;
  timestamp: string;
  category: string;
  actor: string;
  action: string;
  resource: string;
  risk: string;
  details: string;
}

export interface ApiSecurityOverview {
  threats_blocked_30d: number;
  rules_active: number;
  breakdown: ApiSecurityThreatBreakdown[];
  recent_detections: ApiSecurityDetectionItem[];
  threat_trends: {
    date: string;
    prompt_injection: number;
    jailbreak: number;
    data_exfiltration: number;
    secret_leakage: number;
  }[];
}

export interface ApiSecurityScanResponse {
  detected: boolean;
  recommended_action: string;
  highest_severity: string;
  matches: {
    rule_id: string;
    name: string;
    category: string;
    severity: string;
    detail: string;
  }[];
}

export interface ApiOpaStatus {
  enabled: boolean;
  available: boolean;
  policy_path: string;
  fail_open: boolean;
  base_url: string;
  error?: string | null;
}

export interface ApiAbacEvaluateRequest {
  role?: string;
  auth_type?: "jwt" | "client_key";
  actor?: string;
  bundle?: string;
  model?: string;
  routed_model?: string;
  has_pii?: boolean;
  region?: string;
  risk?: "low" | "medium" | "high" | "critical";
  hour_utc?: number;
}

export interface ApiAbacEvaluateResponse {
  allow: boolean;
  available: boolean;
  skipped: boolean;
  violations: { rule: string; message: string; severity: string }[];
  error?: string | null;
}

export interface ApiRoutingModel {
  id: string;
  model: string;
  provider_type: string;
  endpoint_url?: string | null;
  requests: number;
  percentage: number;
  latency: number;
  success_rate: number;
  is_active: boolean;
  api_key_set?: boolean;
  api_key_masked?: string | null;
  cost_per_1m_input?: number;
  cost_per_1m_output?: number;
  model_aliases?: string[];
}

export interface ApiLlmProviderCreateRequest {
  name: string;
  provider_type: string;
  endpoint_url?: string;
  is_active?: boolean;
  api_key?: string;
  model_aliases?: string[];
  cost_per_1m_input?: number;
  cost_per_1m_output?: number;
}

export interface ApiLlmProviderUpdateRequest {
  name?: string;
  provider_type?: string;
  endpoint_url?: string;
  is_active?: boolean;
  percentage?: number;
  api_key?: string;
  model_aliases?: string[];
  cost_per_1m_input?: number;
  cost_per_1m_output?: number;
}

export interface ApiRoutingRule {
  id: string;
  name: string;
  priority: number;
  condition: string;
  target_model: string;
  status: string;
  response_format: "openai" | "anthropic" | "vertex" | "auto";
  target_provider?: string | null;
}

export interface ApiProviderRebalanceResponse {
  total_requests: number;
  providers: {
    id: string;
    model: string;
    requests: number;
    previous_percentage: number;
    percentage: number;
  }[];
  message: string;
}

export interface ApiMcpToolInvokeRequest {
  tool_name: string;
  arguments?: Record<string, unknown>;
}

export interface ApiMcpToolInvokeResponse {
  server_id: string;
  server_name: string;
  ok: boolean;
  message: string;
  result: Record<string, unknown> | null;
  latency_ms: number;
  skipped: boolean;
  session_reused: boolean;
  checked_at: string;
}

export interface ApiRoutingRuleCreateRequest {
  name: string;
  priority?: number;
  condition: string;
  target_model: string;
  status?: string;
  response_format?: "openai" | "anthropic" | "vertex" | "auto";
  target_provider?: string | null;
}

export interface ApiRoutingRuleUpdateRequest {
  name?: string;
  priority?: number;
  condition?: string;
  target_model?: string;
  status?: string;
  response_format?: "openai" | "anthropic" | "vertex" | "auto";
  target_provider?: string | null;
}

export interface ApiRoutingGroupMember {
  model: string;
  weight: number;
  priority: number;
}

export interface ApiRoutingGroup {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  strategy: string;
  members: ApiRoutingGroupMember[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ApiRoutingGroupCreateRequest {
  name: string;
  description?: string;
  strategy?: string;
  members?: ApiRoutingGroupMember[];
  status?: string;
}

export interface ApiRoutingGroupUpdateRequest {
  name?: string;
  description?: string;
  strategy?: string;
  members?: ApiRoutingGroupMember[];
  status?: string;
}

export interface ApiGatewayStatus {
  status: string;
  openai_compatible: boolean;
  gemini_compatible: boolean;
  requests_today: number;
  blocked_today: number;
  endpoints: string[];
  proxy_mode?: string;
  opa_enabled?: boolean;
  opa_available?: boolean;
}

export interface ChatCompletionResponse {
  id: string;
  model: string;
  choices: { message: { role: string; content: string } }[];
  pysetu?: {
    inspection_action?: string;
    violations?: Array<{ rule_name: string; action: string; severity: string; detail: string }>;
    ollama_model?: string;
    routed_model?: string;
    matched_routing_rule?: string;
    routing_strategy?: string;
    upstream?: string;
    policy_bundle?: string;
    client_api_key?: string;
  };
}

export interface ApiPolicyBundle {
  id: string;
  name: string;
  description: string;
  status: string;
  is_default: boolean;
  policy_ids: string[];
  custom_intent_ids: string[];
  policy_names: string[];
  created_at: string;
}

export interface ApiPolicyBundleCreateRequest {
  name: string;
  description?: string;
  status?: string;
  is_default?: boolean;
  policy_ids?: string[];
  custom_intent_ids?: string[];
}

export interface ApiPolicyBundleUpdateRequest {
  name?: string;
  description?: string;
  status?: string;
  is_default?: boolean;
  policy_ids?: string[];
  custom_intent_ids?: string[];
}

export interface ApiClientApiKey {
  id: string;
  name: string;
  description: string;
  key_prefix: string;
  key_masked: string;
  bundle_id: string | null;
  bundle_name: string | null;
  client_response_protocol: string | null;
  ai_rate_limit_rpm: number | null;
  ai_rate_limit_rph: number | null;
  ai_rate_limit_rpd: number | null;
  ai_token_limit_tpm: number | null;
  ai_token_limit_tph: number | null;
  ai_token_limit_tpd: number | null;
  token_saving_enabled: boolean | null;
  token_saving_mode: string | null;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string | null;
}

export interface ApiClientApiKeyCreateRequest {
  name: string;
  description?: string;
  bundle_id?: string;
  client_response_protocol?: string | null;
  ai_rate_limit_rpm?: number | null;
  ai_rate_limit_rph?: number | null;
  ai_rate_limit_rpd?: number | null;
  ai_token_limit_tpm?: number | null;
  ai_token_limit_tph?: number | null;
  ai_token_limit_tpd?: number | null;
  token_saving_enabled?: boolean | null;
  token_saving_mode?: string | null;
}

export interface ApiClientApiKeyCreateResponse extends ApiClientApiKey {
  api_key: string;
}

export interface ApiClientApiKeyUpdateRequest {
  name?: string;
  description?: string;
  bundle_id?: string | null;
  client_response_protocol?: string | null;
  ai_rate_limit_rpm?: number | null;
  ai_rate_limit_rph?: number | null;
  ai_rate_limit_rpd?: number | null;
  ai_token_limit_tpm?: number | null;
  ai_token_limit_tph?: number | null;
  ai_token_limit_tpd?: number | null;
  token_saving_enabled?: boolean | null;
  token_saving_mode?: string | null;
  is_active?: boolean;
}

export interface ApiObservabilityOverview {
  total_events_today: number;
  allowed_today: number;
  blocked_today: number;
  under_review_today: number;
  block_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  error_rate: number;
  by_action: { action: string; count: number }[];
  by_risk: { risk: string; count: number }[];
  daily_trend: { date: string; total: number; blocked: number }[];
}

export interface ApiTelemetrySummary {
  generated_at: string;
  period_days: number;
  total_events: number;
  allowed: number;
  blocked: number;
  under_review: number;
  block_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  active_models: number;
  by_action: { action: string; count: number }[];
  by_risk: { risk: string; count: number }[];
  daily_trend: { date: string; total: number; blocked: number }[];
}

export interface ApiTelemetryBlockedEvent {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource: string;
  risk: string;
  details: string;
}

export interface ApiTelemetryOperations {
  generated_at: string;
  requests_total: number;
  requests_allowed: number;
  requests_blocked: number;
  requests_review: number;
  tokens_total: number;
  prompt_tokens: number;
  completion_tokens: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  block_rate: number;
  by_action: { action: string; count: number }[];
  by_status: { status: string; count: number }[];
  recent_blocked: ApiTelemetryBlockedEvent[];
}

export interface ApiGatewaySla {
  generated_at: string;
  period_days: number;
  requests_total: number;
  successful_requests: number;
  failed_requests: number;
  availability_percent: number;
  error_rate_percent: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  average_gateway_overhead_ms: number;
  providers_active: number;
  pooling_instrumented: boolean;
  pool_reuse_rate_percent: number | null;
  pool_note: string;
}

export interface ApiTraceSpan {
  name: string;
  service: string;
  duration_ms: number;
  status: string;
  stage?: string;
  offset_ms?: number;
  detail?: string | null;
  attributes?: Record<string, unknown> | null;
}

export interface ApiTraceSummary {
  id: string;
  trace_id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource: string;
  status: string;
  risk: string;
  duration_ms: number;
  span_count: number;
  spans: ApiTraceSpan[];
  otel_trace_id?: string | null;
  audit_id?: string | null;
}

export interface ApiIntegrationSettings {
  openai_api_key_set: boolean;
  openai_api_key_masked: string | null;
  gemini_api_key_set: boolean;
  gemini_api_key_masked: string | null;
  gemini_default_model: string;
  ollama_enabled: boolean;
  ollama_base_url: string;
  ollama_default_model: string;
  active_upstream: string;
  streaming_enabled: boolean;
  config_source: string;
  secrets_backend: string;
  vault_auth_method: string | null;
  env_fallback_note: string;
}

export interface ApiAiAssistSettings {
  enabled: boolean;
  provider: "openai" | "gemini" | "groq" | "ollama" | "vllm" | "custom";
  model: string;
  api_key_set: boolean;
  api_key_masked: string | null;
  base_url?: string | null;
  available: boolean;
  uses_gateway_fallback?: boolean;
  credential_source?: string;
  supported_providers?: string[];
  provider_labels?: Record<string, string>;
  features: string[];
  air_gap_mode: boolean;
}

export interface ApiOrganizationSettings {
  id: string;
  name: string;
  slug: string;
  display_name: string;
  logo_url: string | null;
  brand_tagline: string;
  default_product_name: string;
  default_tagline: string;
  qa_dashboard_enabled: boolean;
  features: ApiTenantFeatures;
  feature_policy: ApiTenantFeaturePolicy;
}

export interface ApiIdentitySettings {
  oidc_jit_provision_enabled: boolean;
  platform_jit_default: boolean;
}

export interface ApiPublicTenantBranding {
  slug: string;
  name: string;
  display_name: string;
  logo_url: string | null;
  brand_tagline: string;
}

export interface ApiPublicOidcProvider {
  id: string;
  name: string;
  login_available: boolean;
  message: string;
}

export interface ApiOidcAuthorizeResponse {
  authorization_url: string;
  state: string;
  provider_name: string;
}

export interface ApiOidcProvider {
  id: string;
  name: string;
  issuer_url: string;
  client_id: string;
  scopes: string;
  redirect_uri: string;
  role_claim: string;
  role_mapping: Record<string, string>;
  enabled: boolean;
  created_at: string | null;
  client_secret_set: boolean;
  client_secret_masked: string | null;
}

export interface ApiOidcProviderCreateRequest {
  name: string;
  issuer_url: string;
  client_id: string;
  client_secret?: string;
  scopes?: string;
  redirect_uri?: string;
  role_claim?: string;
  role_mapping?: Record<string, string>;
  enabled?: boolean;
}

export interface ApiOidcProviderUpdateRequest {
  name?: string;
  issuer_url?: string;
  client_id?: string;
  client_secret?: string;
  scopes?: string;
  redirect_uri?: string;
  role_claim?: string;
  role_mapping?: Record<string, string>;
  enabled?: boolean;
}

export interface ApiUagMapping {
  id: string;
  requested_model: string;
  actual_model: string;
  target_provider: string;
  emulate_protocol: string;
  enabled: boolean;
}

export interface ApiUagStats {
  total_translations: number;
  success_rate: number;
  failed_translations: number;
  avg_latency_ms: number;
  compatibility_scores: Record<string, number>;
  route_breakdown: Record<string, number>;
}

export interface ApiUagSettings {
  client_response_protocol: string;
}

export interface ApiUagSimulateResult {
  original_request: Record<string, unknown>;
  canonical: Record<string, unknown>;
  translated_request: Record<string, unknown>;
  trace: Record<string, unknown>;
}

export interface ApiUagPolicy {
  id: string;
  name: string;
  conditions: Record<string, string>;
  actions: Record<string, string>;
  priority: number;
  enabled: boolean;
}

export interface ApiVaultStatus {
  enabled: boolean;
  available: boolean;
  authenticated: boolean;
  addr: string;
  auth_method: string | null;
  mount_path: string;
  secrets_backend: string;
  jwt_from_vault: boolean;
  jwt_secret_insecure: boolean;
  error: string | null;
}

export interface ApiReportKpi {
  label: string;
  value: string;
  change: string;
  trend: string;
}

export interface ApiExecutiveSummary {
  period: string;
  kpis: ApiReportKpi[];
  compliance_score: number;
  frameworks_compliant: number;
  frameworks_total: number;
  top_risks: string[];
  cost_optimization?: {
    layers: {
      id: string;
      label: string;
      tokens_saved: number;
      estimated_usd: number;
      requests: number;
      share_pct: number;
    }[];
    total_tokens_saved: number;
    total_estimated_usd: number;
    narrative: string;
  } | null;
}

export interface ApiReportQuery {
  source: string;
  filters: Record<string, unknown>;
  limit: number;
}

export interface ApiReportSchedule {
  enabled: boolean;
  frequency: string;
  time: string;
  day_of_week: number | null;
  day_of_month: number | null;
  next_run_at: string | null;
  recipients: string[];
}

export interface ApiReportDeliveryRecipient {
  email: string;
  name: string;
  role: string;
}

export interface ApiReportDeliveryRecipientsResponse {
  recipients: ApiReportDeliveryRecipient[];
}

export interface ApiReportCatalogEntry {
  id: string;
  report_uuid: string;
  name: string;
  description: string;
  category: string;
  frequency: string;
  format: string;
  last_generated: string;
  status: string;
  query: ApiReportQuery;
  schedule: ApiReportSchedule;
  is_builtin: boolean;
  stats?: {
    row_count: number;
    generated_at: string | null;
  };
}

export interface ApiReportCatalogResponse {
  reports: ApiReportCatalogEntry[];
}

export interface ApiReportQueryTemplateField {
  key: string;
  label: string;
  type: string;
  options?: string[];
  default?: number | string;
}

export interface ApiReportQueryTemplate {
  source: string;
  label: string;
  description: string;
  filter_fields: ApiReportQueryTemplateField[];
}

export interface ApiReportQueryTemplatesResponse {
  templates: ApiReportQueryTemplate[];
}

export interface ApiReportCreateRequest {
  name: string;
  description?: string;
  category?: string;
  format?: string;
  query?: ApiReportQuery;
  schedule?: Partial<ApiReportSchedule>;
}

export interface ApiReportUpdateRequest {
  name?: string;
  description?: string;
  category?: string;
  format?: string;
  query?: ApiReportQuery;
  schedule?: Partial<ApiReportSchedule>;
}

export interface ApiReportPreviewResponse {
  columns: string[];
  rows: unknown[][];
  row_count: number;
}

export interface ApiReportRunResponse {
  report_id: string;
  columns: string[];
  rows: unknown[][];
  row_count: number;
  generated_at: string;
}

export interface ApiReportSchedulerStatus {
  celery_broker: string;
  smtp_enabled: boolean;
  smtp_host: string;
  due_reports: number;
  mailhog_ui: string | null;
}

export interface ApiReportSchedulerRunDueResponse {
  enqueued: number;
}

export interface ApiQATestCase {
  id: string;
  cycle_id: string;
  case_id: string;
  module: string;
  title: string;
  priority: string;
  method: string;
  status: string;
  notes: string;
  automated_key: string | null;
  tested_by_name: string;
  tested_at: string | null;
  remediation_hint?: string | null;
  linked_defect_code?: string | null;
  suggested_severity?: string | null;
}

export interface ApiQADefect {
  id: string;
  cycle_id: string | null;
  linked_case_id: string | null;
  linked_case_code: string | null;
  defect_code: string;
  severity: string;
  module: string;
  title: string;
  description: string;
  status: string;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface ApiQATestCycleSummary {
  id: string;
  name: string;
  status: string;
  release_decision: string;
  notes: string;
  started_at: string | null;
  completed_at: string | null;
  created_by_name: string;
  created_at: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  blocked_cases: number;
  not_tested_cases: number;
}

export interface ApiQATestCycleDetail extends ApiQATestCycleSummary {
  cases: ApiQATestCase[];
}

export interface ApiQAOverview {
  active_cycle: ApiQATestCycleSummary | null;
  total_cycles: number;
  total_open_defects: number;
  s1_open_defects: number;
  s2_open_defects: number;
  overall_pass_rate: number;
  modules_in_scope: string[];
  release_decision: string;
}

export interface ApiQAAutomatedRunResponse {
  pytest_exit_code: number;
  tests_run: number;
  tests_passed: number;
  tests_failed: number;
  cases_updated: number;
  tests_targeted: number;
  scope: string;
  output_tail: string;
}

export interface ApiQAFileDefectResponse {
  defect: ApiQADefect;
  created: boolean;
}

export const promptTemplatesAPI = {
  list: async (token: string) => {
    return apiFetch<PromptTemplate[]>(`/prompt-templates`, {}, token);
  },
  get: async (token: string, id: string) => {
    return apiFetch<PromptTemplate>(`/prompt-templates/${id}`, {}, token);
  },
  create: async (token: string, data: any) => {
    return apiFetch<PromptTemplate>(`/prompt-templates`, {
      method: "POST",
      body: JSON.stringify(data),
    }, token);
  },
  update: async (token: string, id: string, data: any) => {
    return apiFetch<PromptTemplate>(`/prompt-templates/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }, token);
  },
  delete: async (token: string, id: string) => {
    return apiFetch<void>(`/prompt-templates/${id}`, {
      method: "DELETE",
    }, token);
  },
  addVersion: async (token: string, id: string, data: any) => {
    return apiFetch<PromptVersion>(`/prompt-templates/${id}/versions`, {
      method: "POST",
      body: JSON.stringify(data),
    }, token);
  },
};

export const customIntentsAPI = {
  list: async (token: string) => {
    return apiFetch<CustomIntent[]>(`/governance/custom-intents`, {}, token);
  },
  get: async (token: string, id: string) => {
    return apiFetch<CustomIntent>(`/governance/custom-intents/${id}`, {}, token);
  },
  create: async (token: string, data: CustomIntentCreate) => {
    return apiFetch<CustomIntent>(`/governance/custom-intents`, {
      method: "POST",
      body: JSON.stringify(data),
    }, token);
  },
  update: async (token: string, id: string, data: CustomIntentUpdate) => {
    return apiFetch<CustomIntent>(`/governance/custom-intents/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }, token);
  },
  delete: async (token: string, id: string) => {
    return apiFetch<void>(`/governance/custom-intents/${id}`, {
      method: "DELETE",
    }, token);
  },
  test: async (token: string, prompt: string, intentIds?: string[]) => {
    return apiFetch<CustomIntentTestResponse>(`/governance/custom-intents/test`, {
      method: "POST",
      body: JSON.stringify({ prompt, intent_ids: intentIds }),
    }, token);
  },
};

