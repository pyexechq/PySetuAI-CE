"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Activity, AlertTriangle, ArrowRight, CheckCircle2,
  Filter, MoreHorizontal, Plus, Search,
  Server, Settings2, Trash2, Users,
  XCircle, Network, Wifi, Globe, Wand2, Shield, Key,
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { McpServerModal } from "@/components/mcp-governance/mcp-server-modal";
import { DynamicToolCallingCard } from "@/components/mcp-governance/dynamic-tool-calling-card";
import { McpMultiplexCard } from "@/components/mcp-governance/mcp-multiplex-card";
import { McpCatalogCard } from "@/components/mcp-governance/mcp-catalog-card";
import { McpOAuthBrokerCard } from "@/components/mcp-governance/mcp-oauth-broker-card";
import { McpToolRiskCard } from "@/components/mcp-governance/mcp-tool-risk-card";
import { McpAgentTogglesCard } from "@/components/mcp-governance/mcp-agent-toggles-card";
import { McpPortalSettingsCard } from "@/components/mcp-governance/mcp-portal-settings-card";
import { McpUrlFilterCard } from "@/components/mcp-governance/mcp-url-filter-card";
import { McpToolDenyListCard } from "@/components/mcp-governance/mcp-tool-deny-list-card";
import { McpSsoInjectionCard } from "@/components/mcp-governance/mcp-sso-injection-card";
import { McpDeveloperGrantsCard } from "@/components/mcp-governance/mcp-developer-grants-card";
import { RestToMcpWizardModal } from "@/components/mcp-governance/rest-to-mcp-wizard-modal";
import { McpPortalView } from "@/components/mcp-portal/mcp-portal-view";
import { useMcpServers } from "@/hooks/use-mcp-servers";
import { api, ApiError, type ApiMcpServer } from "@/lib/api";
import { formatNumber, cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { usePreferencesStore } from "@/stores/preferences-store";

// ─── types & helpers ──────────────────────────────────────────────────────────

type Tab = "overview" | "servers" | "tools" | "access" | "settings";

const ALL_TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "servers", label: "MCP Servers" },
  { id: "tools", label: "Tools" },
  { id: "access", label: "Access & RBAC" },
  { id: "settings", label: "Platform Settings" },
];

const PORTAL_ONLY_TABS: { id: Tab; label: string }[] = [{ id: "overview", label: "Overview" }];

const TAB_IDS = new Set<string>(ALL_TABS.map((tab) => tab.id));

function parseTabParam(value: string | null, portalOnly: boolean): Tab | null {
  if (!value || !TAB_IDS.has(value)) return null;
  return value as Tab;
}

const statusVariant = {
  healthy: "success" as const,
  degraded: "warning" as const,
  offline: "destructive" as const,
};

function riskOf(score: number): "Low" | "Medium" | "High" {
  if (score >= 71) return "Low";
  if (score >= 41) return "Medium";
  return "High";
}

function riskVariant(risk: string) {
  if (risk === "High") return "destructive" as const;
  if (risk === "Medium") return "warning" as const;
  return "success" as const;
}

function protocolIcon(transport: string) {
  if (transport === "sse") return <Network className="h-3.5 w-3.5" />;
  if (transport === "http") return <Wifi className="h-3.5 w-3.5" />;
  return <Globe className="h-3.5 w-3.5" />;
}

// ─── TabBar ───────────────────────────────────────────────────────────────────

function TabBar({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: Tab; label: string }[];
  active: Tab;
  onChange: (t: Tab) => void;
}) {
  if (tabs.length <= 1) return null;

  return (
    <div className="flex items-center gap-1.5 overflow-x-auto p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs mb-6">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={cn(
            "px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all whitespace-nowrap shrink-0",
            active === tab.id
              ? "bg-primary text-primary-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// ─── TrustScoreBar ────────────────────────────────────────────────────────────

function TrustScoreBar({ score }: { score: number }) {
  const barColor =
    score >= 71 ? "bg-emerald-500" : score >= 41 ? "bg-amber-500" : "bg-rose-500";
  const textColor =
    score >= 71 ? "text-emerald-400" : score >= 41 ? "text-amber-400" : "text-rose-400";
  return (
    <div className="w-full">
      <span className={cn("text-xs font-semibold tabular-nums", textColor)}>{score}</span>
      <div className="w-full bg-muted rounded-full h-1.5 mt-1">
        <div
          className={cn("h-1.5 rounded-full transition-all", barColor)}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

// ─── main view ────────────────────────────────────────────────────────────────

export function McpGovernanceView() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const router = useRouter();
  const searchParams = useSearchParams();
  usePreferencesStore((s) => s.timezone);
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";
  const canGovern =
    user?.role === "tenant_admin" ||
    user?.role === "security_admin" ||
    user?.role === "platform_admin";
  const portalOnly = false;
  const tabs = ALL_TABS;
  const defaultTab: Tab = "overview";

  const [activeTab, setActiveTab] = useState<Tab>(
    () => parseTabParam(searchParams.get("tab"), portalOnly) ?? defaultTab
  );
  const [toolSearch, setToolSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<ApiMcpServer | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false); // BL-083
  const [actionError, setActionError] = useState<string | null>(null);
  const [checkingAll, setCheckingAll] = useState(false);
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [discoveringId, setDiscoveringId] = useState<string | null>(null);

  const { data: servers = [], isLoading, invalidateMcpServers } = useMcpServers();

  useEffect(() => {
    const tab = parseTabParam(searchParams.get("tab"), portalOnly);
    if (tab) setActiveTab(tab);
  }, [searchParams, portalOnly]);

  function handleTabChange(tab: Tab) {
    setActiveTab(tab);
    router.replace(`/mcp-governance?tab=${tab}`, { scroll: false });
  }

  // KPI aggregates
  const activeCount = servers.filter((s) => s.status === "healthy").length;
  const highRiskCount = servers.filter((s) => riskOf(s.trustScore ?? 0) === "High").length;
  const blockedCount = servers.filter((s) => s.status === "offline").length;
  const totalToolCalls = servers.reduce((sum, s) => sum + s.totalCalls, 0);

  // All tools flattened for the Tools tab
  const allTools = useMemo(
    () =>
      servers.flatMap((s) =>
        (s.toolNames ?? []).map((name) => ({
          name,
          server: s.name,
          risk: riskOf(s.trustScore ?? 0),
          dailyCalls: s.totalCalls,
          latency: s.avgLatency,
          status: s.status,
        }))
      ),
    [servers]
  );

  const filteredTools = toolSearch
    ? allTools.filter(
        (t) =>
          t.name.toLowerCase().includes(toolSearch.toLowerCase()) ||
          t.server.toLowerCase().includes(toolSearch.toLowerCase())
      )
    : allTools;

  // Trust distribution for donut
  const trustDist = [
    { name: "High (71-100)", value: servers.filter((s) => (s.trustScore ?? 0) >= 71).length, color: "#10b981" },
    { name: "Medium (41-70)", value: servers.filter((s) => { const ts = s.trustScore ?? 0; return ts >= 41 && ts < 71; }).length, color: "#f59e0b" },
    { name: "Low (0-40)", value: servers.filter((s) => (s.trustScore ?? 0) < 41).length, color: "#ef4444" },
  ];

  const categories = ["All", ...Array.from(new Set(servers.map((s) => s.category)))];

  // ── handlers (unchanged from original) ──────────────────────────────────────

  function openCreateModal() { setEditingServer(null); setModalOpen(true); }

  function openEditModal(server: (typeof servers)[0]) {
    setEditingServer({
      id: server.id, name: server.name, category: server.category,
      success_rate: server.successRate, avg_latency: server.avgLatency,
      total_calls: server.totalCalls, status: server.status,
      tools: server.tools, tool_names: server.toolNames,
      trust_score: server.trustScore, risk_score: server.riskScore,
      endpoint_url: server.endpointUrl, transport: server.transport,
      connection_config: server.connectionConfig,
    });
    setModalOpen(true);
  }

  async function removeServer(server: (typeof servers)[0]) {
    if (!token) return;
    if (!window.confirm(`Remove MCP server "${server.name}" from inventory?`)) return;
    setActionError(null);
    try { await api.deleteMcpServer(token, server.id); invalidateMcpServers(); }
    catch (err) { setActionError(err instanceof ApiError ? err.message : "Failed to remove MCP server"); }
  }

  async function runHealthCheck(server: (typeof servers)[0]) {
    if (!token) return;
    setActionError(null); setCheckingId(server.id);
    try {
      const result = await api.checkMcpServerHealth(token, server.id);
      invalidateMcpServers();
      if (!result.ok && !result.skipped) setActionError(`${server.name}: ${result.message}`);
    } catch (err) { setActionError(err instanceof ApiError ? err.message : "Health check failed"); }
    finally { setCheckingId(null); }
  }

  async function discoverTools(server: (typeof servers)[0]) {
    if (!token) return;
    setActionError(null); setDiscoveringId(server.id);
    try {
      const result = await api.discoverMcpServerTools(token, server.id);
      invalidateMcpServers();
      if (!result.ok && !result.skipped) setActionError(`${server.name}: ${result.message}`);
    } catch (err) { setActionError(err instanceof ApiError ? err.message : "Tool discovery failed"); }
    finally { setDiscoveringId(null); }
  }

  async function runAllHealthChecks() {
    if (!token) return;
    setActionError(null); setCheckingAll(true);
    try {
      const batch = await api.checkAllMcpServersHealth(token);
      invalidateMcpServers();
      const failed = batch.results.filter((r) => !r.ok && !r.skipped);
      if (failed.length > 0)
        setActionError(`${failed.length} server(s) need attention: ${failed.map((r) => r.server_name).join(", ")}`);
    } catch (err) { setActionError(err instanceof ApiError ? err.message : "Health checks failed"); }
    finally { setCheckingAll(false); }
  }

  // ── render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-4 sm:p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between w-full min-w-0">
          <div className="space-y-2.5 w-full min-w-0 max-w-xl">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                MCP Circuit Breakers Active
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <Shield className="h-3.5 w-3.5 text-primary" />
                Zero-Trust Agent Sandbox
              </Badge>
              <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-xs font-mono">
                OAuth 2.0 Broker
              </Badge>
            </div>

            <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-foreground break-words">
              Agentic Security & MCP Tool Governance
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Real-time tool multiplexing, rogue agent circuit breakers, blast-radius mitigation, argument schema validation, and granular role-based grants across all MCP servers.
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-2.5 sm:gap-3 w-full lg:w-auto shrink-0">
            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">MCP Servers</span>
                <Server className="h-3.5 w-3.5 text-primary" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-foreground">{servers.length}</p>
              <p className="text-[10px] text-muted-foreground">{activeCount} healthy</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">High Risk Tools</span>
                <AlertTriangle className="h-3.5 w-3.5 text-rose-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-rose-600 dark:text-rose-400">{highRiskCount}</p>
              <p className="text-[10px] text-muted-foreground">Sandboxed</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Tool Invocations</span>
                <Activity className="h-3.5 w-3.5 text-blue-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-foreground">{formatNumber(totalToolCalls)}</p>
              <p className="text-[10px] text-muted-foreground">Governed executions</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Discovered Tools</span>
                <Wand2 className="h-3.5 w-3.5 text-amber-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-foreground">{allTools.length}</p>
              <p className="text-[10px] text-muted-foreground">In active catalog</p>
            </div>
          </div>
        </div>
      </div>

      {/* Page header action bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        <TabBar tabs={tabs} active={activeTab} onChange={handleTabChange} />

        {canEdit && !portalOnly && (
          <div className="flex flex-wrap items-center gap-2 mb-6">
            <Button
              size="sm" variant="outline" className="gap-1.5 text-xs h-8"
              disabled={checkingAll || servers.length === 0}
              onClick={runAllHealthChecks}
            >
              <Activity className={cn("h-3.5 w-3.5", checkingAll && "animate-pulse")} />
              {checkingAll ? "Checking…" : "Run Health Checks"}
            </Button>
            <Button
              size="sm" variant="outline" className="gap-1.5 text-xs h-8 border-indigo-500/40 text-indigo-400 hover:bg-indigo-500/10"
              onClick={() => setWizardOpen(true)}
            >
              <Wand2 className="h-3.5 w-3.5" />
              Import API Spec
            </Button>
            <Button size="sm" className="gap-1.5 text-xs h-8" onClick={openCreateModal}>
              <Plus className="h-3.5 w-3.5" />
              Register MCP Server
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 text-xs h-8 border-primary/40 text-primary hover:bg-primary/10 font-bold"
              onClick={() => window.open('/developer-portal', '_blank')}
            >
              <Globe className="h-3.5 w-3.5" />
              Developer Portal ↗
            </Button>
          </div>
        )}
      </div>

      {actionError && <p className="mb-3 text-sm text-red-400">{actionError}</p>}

      {/* ── OVERVIEW ──────────────────────────────────────────────────────────── */}
      {canGovern && activeTab === "overview" && (
        <div className="space-y-6">
          {/* KPI row */}
          <div className="grid gap-4 sm:grid-cols-5">
            {[
              { label: "Total MCP Servers", value: servers.length, color: "" },
              { label: "Active / Healthy", value: activeCount, color: "text-emerald-400" },
              { label: "High Risk", value: highRiskCount, color: "text-rose-400" },
              { label: "Offline / Blocked", value: blockedCount, color: "text-amber-400" },
              { label: "Total Tool Calls", value: formatNumber(totalToolCalls), color: "text-primary" },
            ].map((kpi) => (
              <Card key={kpi.label} className="border-border/60 bg-card/50">
                <CardContent className="p-5">
                  <p className="text-xs text-muted-foreground mb-1">{kpi.label}</p>
                  <p className={cn("text-3xl font-bold", kpi.color)}>{kpi.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-12">
            {/* Server summary table */}
            <Card className="lg:col-span-8 border-border/60 bg-card/50">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="text-sm font-semibold">MCP Servers</CardTitle>
                <button
                  type="button"
                  onClick={() => handleTabChange("servers")}
                  className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
                >
                  View all <ArrowRight className="h-3 w-3" />
                </button>
              </CardHeader>
              <CardContent className="p-0">
                {isLoading ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>
                ) : servers.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">No MCP servers registered</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border/60">
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Server</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Protocol</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Tools</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground w-36">Trust Score</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Risk</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                      {servers.map((s) => (
                        <tr key={s.id} className="hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-3 font-medium">{s.name}</td>
                          <td className="px-4 py-3">
                            <span className="flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
                              {protocolIcon(s.transport ?? "sse")}
                              {(s.transport ?? "sse").toUpperCase()}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">{s.tools}</td>
                          <td className="px-4 py-3"><TrustScoreBar score={s.trustScore ?? 0} /></td>
                          <td className="px-4 py-3">
                            <Badge variant={riskVariant(riskOf(s.trustScore ?? 0))}>{riskOf(s.trustScore ?? 0)}</Badge>
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={statusVariant[s.status]}>{s.status}</Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </CardContent>
            </Card>

            {/* Trust score donut */}
            <Card className="lg:col-span-4 border-border/60 bg-card/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Trust Score Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={trustDist}
                        innerRadius={52}
                        outerRadius={72}
                        paddingAngle={4}
                        dataKey="value"
                        stroke="none"
                      >
                        {trustDist.map((entry) => (
                          <Cell key={entry.name} fill={entry.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-2xl font-bold">{servers.length}</span>
                    <span className="text-xs text-muted-foreground">Total</span>
                  </div>
                </div>
                <div className="mt-2 space-y-1.5">
                  {trustDist.map((d) => (
                    <div key={d.name} className="flex justify-between items-center text-xs text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                        {d.name}
                      </span>
                      <span className="font-semibold tabular-nums">{d.value}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recent alerts feed */}
          <Card className="border-border/60 bg-card/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Recent Alerts</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {highRiskCount === 0 && blockedCount === 0 ? (
                <div className="flex items-center gap-2 text-sm text-emerald-400">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  No active alerts — all servers within policy thresholds
                </div>
              ) : (
                <>
                  {servers.filter((s) => riskOf(s.trustScore ?? 0) === "High").slice(0, 3).map((s) => (
                    <div key={`hr-${s.id}`} className="flex items-start justify-between rounded-lg border border-rose-500/20 bg-rose-500/5 p-3">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className="h-4 w-4 text-rose-400 mt-0.5 shrink-0" />
                        <div>
                          <p className="text-sm font-medium">High risk server: {s.name}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">Trust score {s.trustScore ?? 0} — review access policies</p>
                        </div>
                      </div>
                      <Badge variant="destructive">High Risk</Badge>
                    </div>
                  ))}
                  {servers.filter((s) => s.status === "offline").slice(0, 2).map((s) => (
                    <div key={`off-${s.id}`} className="flex items-start justify-between rounded-lg border border-rose-500/20 bg-rose-500/5 p-3">
                      <div className="flex items-start gap-3">
                        <XCircle className="h-4 w-4 text-rose-400 mt-0.5 shrink-0" />
                        <div>
                          <p className="text-sm font-medium">Server offline: {s.name}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">Health check failed — connection unreachable</p>
                        </div>
                      </div>
                      <Badge variant="destructive">Offline</Badge>
                    </div>
                  ))}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── MCP SERVERS (card grid) ───────────────────────────────────────────── */}
      {canGovern && activeTab === "servers" && (
        <div>
          {isLoading ? (
            <p className="py-12 text-center text-sm text-muted-foreground">Loading MCP servers…</p>
          ) : servers.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-sm text-muted-foreground">No MCP servers registered</p>
              {canEdit && (
                <Button size="sm" className="mt-3 gap-1.5" onClick={openCreateModal}>
                  <Plus className="h-4 w-4" /> Add your first server
                </Button>
              )}
            </div>
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {servers.map((server) => {
                const risk = riskOf(server.trustScore ?? 0);
                const trustNum = server.trustScore ?? 0;
                return (
                  <div
                    key={server.id}
                    className="rounded-xl border border-border/60 bg-card/50 p-5 flex flex-col hover:border-border/90 transition-colors"
                  >
                    {/* Card header */}
                    <div className="flex justify-between items-start mb-4">
                      <div className="w-10 h-10 rounded-lg border border-border/60 bg-muted/40 flex items-center justify-center">
                        <Server className={cn("h-5 w-5", server.status === "healthy" ? "text-primary" : "text-muted-foreground")} />
                      </div>
                      <div className="flex flex-col items-end gap-1.5">
                        <Badge variant={statusVariant[server.status]}>{server.status}</Badge>
                        <span className="text-[10px] font-mono text-muted-foreground border border-border/60 rounded px-1.5 py-0.5 bg-muted/30 flex items-center gap-1">
                          {protocolIcon(server.transport ?? "sse")}
                          {(server.transport ?? "sse").toUpperCase()}
                        </span>
                      </div>
                    </div>

                    <h3 className="text-base font-bold mb-1">{server.name}</h3>
                    <p className="text-xs text-muted-foreground mb-4 flex items-center gap-1">
                      <Users className="h-3 w-3 shrink-0" /> {server.category}
                    </p>

                    {/* Stats grid */}
                    <div className="grid grid-cols-2 gap-3 mb-4 flex-1">
                      <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                        <p className="text-xs text-muted-foreground mb-1">Exposed Tools</p>
                        <p className="text-lg font-bold">{server.tools}</p>
                      </div>
                      <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                        <p className="text-xs text-muted-foreground mb-1">Success Rate</p>
                        <p className="text-lg font-bold text-emerald-400">{server.successRate}%</p>
                      </div>
                    </div>

                    {/* Trust score bar */}
                    <div className="mb-4">
                      <div className="flex justify-between text-xs text-muted-foreground mb-1">
                        <span>Trust Score</span>
                        <span className={cn(
                          "font-semibold",
                          trustNum >= 71 ? "text-emerald-400" : trustNum >= 41 ? "text-amber-400" : "text-rose-400"
                        )}>{trustNum}</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className={cn(
                            "h-2 rounded-full transition-all",
                            trustNum >= 71 ? "bg-emerald-500" : trustNum >= 41 ? "bg-amber-500" : "bg-rose-500"
                          )}
                          style={{ width: `${trustNum}%` }}
                        />
                      </div>
                    </div>

                    {/* Footer */}
                    <div className="border-t border-border/50 pt-3 flex justify-between items-center">
                      <Badge variant={riskVariant(risk)}>{risk} Risk</Badge>
                      {canEdit && (
                        <div className="flex gap-1">
                          <Button
                            type="button" variant="ghost" size="sm"
                            className="h-7 w-7 p-0"
                            disabled={checkingId === server.id || checkingAll}
                            onClick={() => runHealthCheck(server)}
                            aria-label={`Health check ${server.name}`}
                          >
                            <Activity className={cn("h-3.5 w-3.5", checkingId === server.id && "animate-pulse text-primary")} />
                          </Button>
                          <Button
                            type="button" variant="ghost" size="sm"
                            className="h-7 w-7 p-0"
                            disabled={discoveringId === server.id || server.transport === "stdio"}
                            onClick={() => discoverTools(server)}
                            aria-label={`Discover tools for ${server.name}`}
                          >
                            <Search className={cn("h-3.5 w-3.5", discoveringId === server.id && "animate-pulse text-primary")} />
                          </Button>
                          <Button
                            type="button" variant="ghost" size="sm"
                            className="h-7 px-2 text-xs gap-1"
                            onClick={() => openEditModal(server)}
                          >
                            <Settings2 className="h-3 w-3" /> Edit
                          </Button>
                          <Button
                            type="button" variant="ghost" size="sm"
                            className="h-7 px-2 text-xs gap-1 text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => removeServer(server)}
                          >
                            <Trash2 className="h-3 w-3" /> Remove
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── TOOLS ──────────────────────────────────────────────────────────────── */}
      {canGovern && activeTab === "tools" && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 pb-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search tools or servers…"
                value={toolSearch}
                onChange={(e) => setToolSearch(e.target.value)}
                className="w-full rounded-lg border border-border/60 bg-muted/30 pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Filter className="h-3.5 w-3.5" />
              {filteredTools.length} tool{filteredTools.length !== 1 ? "s" : ""}
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {allTools.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No tools discovered yet. Run tool discovery on connected servers.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/60">
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Tool Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Parent Server</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Risk</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">Daily Calls</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">Avg Latency</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Status</th>
                    <th className="px-4 py-3 w-8" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {filteredTools.map((tool, i) => (
                    <tr key={`${tool.name}-${i}`} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-primary font-medium">{tool.name}</td>
                      <td className="px-4 py-3">
                        <span className="flex items-center gap-1.5 text-muted-foreground">
                          <Server className="h-3.5 w-3.5 shrink-0" />
                          {tool.server}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={riskVariant(tool.risk)}>{tool.risk}</Badge>
                      </td>
                      <td className="px-4 py-3 text-right text-muted-foreground tabular-nums">{formatNumber(tool.dailyCalls)}</td>
                      <td className="px-4 py-3 text-right text-muted-foreground tabular-nums">{tool.latency}ms</td>
                      <td className="px-4 py-3">
                        <Badge variant={statusVariant[tool.status as keyof typeof statusVariant] ?? "outline"}>
                          {tool.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button className="text-muted-foreground hover:text-foreground transition-colors">
                          <MoreHorizontal className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── ACCESS & RBAC ─────────────────────────────────────────────────────── */}
      {canGovern && activeTab === "access" && (
        <div className="space-y-8">
          {/* 1. Developer Portal Access Grants & Authorized Users */}
          <McpDeveloperGrantsCard canEdit={canEdit} />

          {/* 2. Identity & Credential Broker Section */}
          <div className="pt-2">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <Key className="w-4 h-4 text-primary" />
                Identity &amp; Credential Broker
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Configure user identity forwarding, SSO context propagation, and OAuth2 broker settings for downstream MCP servers.
              </p>
            </div>
            <div className="space-y-6">
              <McpSsoInjectionCard canEdit={canEdit} />
              <McpOAuthBrokerCard canEdit={canEdit} />
            </div>
          </div>

          {/* 3. Agent Policies & Tool Guardrails Section */}
          <div className="pt-2">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary" />
                Agent Policies &amp; Tool Guardrails
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Enforce risk tiers, per-agent capability toggles, and global tool deny lists.
              </p>
            </div>
            <div className="space-y-6">
              <McpAgentTogglesCard canEdit={canEdit} />
              <McpToolRiskCard canEdit={canEdit} />
              <McpToolDenyListCard canEdit={canEdit} />
            </div>
          </div>
        </div>
      )}

      {/* ── PLATFORM SETTINGS ────────────────────────────────────────────────── */}
      {canGovern && activeTab === "settings" && (
        <div className="space-y-6">
          <McpMultiplexCard />
          <McpCatalogCard canEdit={canEdit} onInstalled={invalidateMcpServers} />
          <McpPortalSettingsCard canEdit={canEdit} />
          <McpUrlFilterCard canEdit={canEdit} />
          <DynamicToolCallingCard canEdit={canEdit} />
        </div>
      )}

      {/* Modals */}
      <McpServerModal
        open={modalOpen}
        server={editingServer}
        token={token}
        categorySuggestions={categories.filter((c) => c !== "All")}
        onClose={() => setModalOpen(false)}
        onSaved={invalidateMcpServers}
      />
      <RestToMcpWizardModal
        open={wizardOpen}
        token={token}
        categorySuggestions={categories.filter((c) => c !== "All")}
        onClose={() => setWizardOpen(false)}
        onSaved={invalidateMcpServers}
      />
    </div>
  );
}
