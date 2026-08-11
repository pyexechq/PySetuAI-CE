import { handleSessionExpired } from "@/lib/session";

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

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    let message = text;
    try {
      const json = JSON.parse(text) as { error?: { message?: string }; detail?: string };
      message = json.error?.message ?? json.detail ?? text;
    } catch {
      // keep raw text
    }
    if (response.status === 401) {
      handleSessionExpired();
      throw new ApiError("Session expired. Please sign in again.", 401);
    }
    throw new ApiError(message || `Request failed (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
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
  helixguard_module?: string | null;
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

export interface ApiDashboardOverview {
  metrics: ApiDashboardMetrics;
  traffic: { date: string; total_requests: number; blocked_requests: number }[];
  risk_distribution: { level: string; count: number; percentage: number }[];
  top_threats: { name: string; count: number }[];
  llm_usage: { model: string; percentage: number; requests: number }[];
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

export interface ApiPlatformTenant {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string | null;
  demo_data_loaded: boolean;
  admin_email: string | null;
}

export interface ApiPlatformTenantCreateRequest {
  name: string;
  slug: string;
  admin_email: string;
  admin_name: string;
  admin_password: string;
  include_demo_data?: boolean;
  is_active?: boolean;
}

export interface ApiPlatformTenantUpdateRequest {
  name?: string;
  is_active?: boolean;
}

export interface ApiPlatformTenantProvisionResult {
  tenant: ApiPlatformTenant;
  demo_users: { email: string; name: string; role: string; password: string }[];
  message: string;
}

export interface LoginPayload {
  email: string;
  password: string;
  tenant_slug?: string;
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

  getOrganizationSettings: (token: string) =>
    apiFetch<ApiOrganizationSettings>("/settings/organization", {}, token),

  updateOrganizationSettings: (
    token: string,
    body: {
      name?: string;
      display_name?: string;
      logo_url?: string;
      brand_tagline?: string;
    }
  ) =>
    apiFetch<ApiOrganizationSettings>("/settings/organization", {
      method: "PUT",
      body: JSON.stringify(body),
    }, token),

  getPublicTenantBranding: (tenantSlug: string) =>
    apiFetch<ApiPublicTenantBranding>(`/tenants/branding/${encodeURIComponent(tenantSlug)}`),

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

  listOidcProviders: (token: string) =>
    apiFetch<ApiOidcProvider[]>("/settings/oidc", {}, token),

  createOidcProvider: (token: string, body: ApiOidcProviderCreateRequest) =>
    apiFetch<ApiOidcProvider>("/settings/oidc", { method: "POST", body: JSON.stringify(body) }, token),

  deleteOidcProvider: (token: string, providerId: string) =>
    apiFetch<void>(`/settings/oidc/${providerId}`, { method: "DELETE" }, token),

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

  getNotifications: (token: string, readIds: string[] = [], limit = 30) => {
    const query = new URLSearchParams({ limit: String(limit) });
    if (readIds.length > 0) query.set("read", readIds.join(","));
    return apiFetch<ApiNotificationListResponse>(`/notifications?${query.toString()}`, {}, token);
  },

  getMcpServers: (token: string) =>
    apiFetch<ApiMcpServer[]>("/mcp/servers", {}, token),

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

  getAuditLogs: (token: string, params?: { search?: string; status?: string; since?: string; limit?: number; from_date?: string; to_date?: string }) => {
    const query = new URLSearchParams();
    if (params?.search) query.set("search", params.search);
    if (params?.status) query.set("status", params.status);
    if (params?.since) query.set("since", params.since);
    if (params?.limit) query.set("limit", String(params.limit));
    appendDateRange(query, params);
    const qs = query.toString();
    return apiFetch<ApiAuditLog[]>(`/audit/logs${qs ? `?${qs}` : ""}`, {}, token);
  },

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

  getPolicyRules: (token: string, policyId?: string) => {
    const query = policyId ? `?policy_id=${encodeURIComponent(policyId)}` : "";
    return apiFetch<ApiPolicyRule[]>(`/policies/rules${query}`, {}, token);
  },

  savePolicyRules: (token: string, policyId: string, body: ApiPolicyRulesSaveRequest) =>
    apiFetch<ApiPolicyRule[]>(`/policies/${policyId}/rules`, { method: "PUT", body: JSON.stringify(body) }, token),

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
    }
  ) =>
    apiFetch<ChatCompletionResponse>(
      "/v1/chat/completions",
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
    const response = await fetch(`${API_BASE}/v1/chat/completions`, {
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
        const filename = match?.[1] ?? `helixguard-${reportId}.csv`;
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
};

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
    tool_schemas?: ApiMcpToolSchema[];
    mcp_session?: Record<string, unknown>;
  };
  trust_score: number;
  risk_score: number;
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
  requests: number;
  percentage: number;
  latency: number;
  success_rate: number;
  is_active: boolean;
  api_key_set?: boolean;
  api_key_masked?: string | null;
}

export interface ApiLlmProviderCreateRequest {
  name: string;
  provider_type: string;
  is_active?: boolean;
  api_key?: string;
}

export interface ApiLlmProviderUpdateRequest {
  name?: string;
  provider_type?: string;
  is_active?: boolean;
  percentage?: number;
  api_key?: string;
}

export interface ApiRoutingRule {
  id: string;
  name: string;
  priority: number;
  condition: string;
  target_model: string;
  status: string;
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
}

export interface ApiRoutingRuleUpdateRequest {
  name?: string;
  priority?: number;
  condition?: string;
  target_model?: string;
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
}

export interface ChatCompletionResponse {
  id: string;
  model: string;
  choices: { message: { role: string; content: string } }[];
  helixguard?: {
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
  policy_names: string[];
  created_at: string;
}

export interface ApiPolicyBundleCreateRequest {
  name: string;
  description?: string;
  status?: string;
  is_default?: boolean;
  policy_ids?: string[];
}

export interface ApiPolicyBundleUpdateRequest {
  name?: string;
  description?: string;
  status?: string;
  is_default?: boolean;
  policy_ids?: string[];
}

export interface ApiClientApiKey {
  id: string;
  name: string;
  description: string;
  key_prefix: string;
  key_masked: string;
  bundle_id: string | null;
  bundle_name: string | null;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string | null;
}

export interface ApiClientApiKeyCreateRequest {
  name: string;
  description?: string;
  bundle_id?: string;
}

export interface ApiClientApiKeyCreateResponse extends ApiClientApiKey {
  api_key: string;
}

export interface ApiClientApiKeyUpdateRequest {
  name?: string;
  description?: string;
  bundle_id?: string | null;
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

export interface ApiTraceSpan {
  name: string;
  service: string;
  duration_ms: number;
  status: string;
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

export interface ApiOrganizationSettings {
  id: string;
  name: string;
  slug: string;
  display_name: string;
  logo_url: string | null;
  brand_tagline: string;
  default_product_name: string;
  default_tagline: string;
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
