"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { Pencil, Plus, RefreshCw, Trash2, Cpu, Cloud, Zap, DollarSign, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LlmProviderModal } from "@/components/llm-router/llm-provider-modal";
import { RoutingRuleModal } from "@/components/llm-router/routing-rule-modal";
import { RoutingGroupModal } from "@/components/llm-router/routing-group-modal";
import { AssignClientKeyModal } from "@/components/llm-router/assign-client-key-modal";
import { useLlmRouting } from "@/hooks/use-llm-routing";
import { api, ApiError, type ApiRoutingModel, type ApiRoutingRule, type ApiRoutingGroup, type ApiClientApiKey } from "@/lib/api";
import { formatNumber, cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

// ─── types ────────────────────────────────────────────────────────────────────

type Tab = "rules" | "models" | "groups" | "performance" | "cost";

const TABS: { id: Tab; label: string }[] = [
  { id: "rules", label: "Routing Rules" },
  { id: "models", label: "Model Registry" },
  { id: "groups", label: "Routing Groups" },
  { id: "performance", label: "Performance" },
  { id: "cost", label: "Cost" },
];

// ─── TabBar ───────────────────────────────────────────────────────────────────

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <div className="flex border-b border-border/60 mb-6 gap-6 overflow-x-auto">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={cn(
            "pb-3 text-sm font-medium transition-colors relative whitespace-nowrap shrink-0",
            active === tab.id
              ? "text-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {tab.label}
          {active === tab.id && (
            <div className="absolute bottom-0 left-0 w-full h-0.5 bg-primary rounded-full" />
          )}
        </button>
      ))}
    </div>
  );
}

// ─── RoutingVisualEngine ─────────────────────────────────────────────────────
// Vertical workflow: Incoming Request → Routing Engine → fanned-out model cards

interface RoutingVisualEngineProps {
  rule: { name: string; condition: string; targetModel: string } | null;
  models: { model: string; color: string; percentage: number; providerType?: string | null }[];
}

type LaneKind = "cost" | "perf" | "secure";

function laneForTarget(name: string, type: string): LaneKind {
  const t = (type || "").toLowerCase();
  const n = name.toLowerCase();
  if (t === "ollama" || t === "custom" || n.includes("llama")) return "secure";
  if (t === "gemini" || n.includes("mini") || n.includes("flash") || n.includes("haiku")) return "cost";
  return "perf";
}

const LANE_STYLES: Record<LaneKind, { dot: string; ring: string; label: string }> = {
  cost: { dot: "bg-emerald-500", ring: "ring-emerald-500/40", label: "Low cost" },
  perf: { dot: "bg-sky-500", ring: "ring-sky-500/40", label: "High performance" },
  secure: { dot: "bg-violet-500", ring: "ring-violet-500/40", label: "Air-gapped" },
};

function providerLabel(type: string): string {
  const t = (type || "").toLowerCase();
  if (t === "openai") return "OpenAI";
  if (t === "anthropic") return "Anthropic";
  if (t === "gemini") return "Google";
  if (t === "ollama") return "Air-gapped";
  if (t === "bedrock") return "Bedrock";
  if (t === "vertex") return "Vertex";
  return type || "Cloud";
}

function RoutingVisualEngine({ rule, models }: RoutingVisualEngineProps) {
  const [showTraffic, setShowTraffic] = useState(true);

  if (!rule) {
    return (
      <div className="flex h-56 items-center justify-center rounded-xl border border-dashed border-border/60 text-sm text-muted-foreground">
        Select a routing rule to visualise the workflow
      </div>
    );
  }

  const targetNames = rule.targetModel
    ? rule.targetModel.split(",").map((s) => s.trim()).filter(Boolean)
    : [];

  const targets = (targetNames.length > 0
    ? targetNames.map((name) => {
        const m = models.find((mo) => mo.model === name);
        return {
          name,
          color: m?.color ?? "#38bdf8",
          pct: m?.percentage ?? 0,
          type: m?.providerType ?? "cloud",
        };
      })
    : models.slice(0, 4).map((m) => ({
        name: m.model,
        color: m.color,
        pct: m.percentage,
        type: m.providerType ?? "cloud",
      }))
  ).slice(0, 4);

  const fallbackTargets =
    targets.length > 0
      ? targets
      : [{ name: "Default pool", color: "#38bdf8", pct: 100, type: "cloud" }];

  const pctSum = fallbackTargets.reduce((s, t) => s + (t.pct || 0), 0);
  const shares = fallbackTargets.map((t) =>
    pctSum > 0 ? Math.max(1, Math.round((t.pct / pctSum) * 100)) : Math.round(100 / fallbackTargets.length)
  );
  const shareAdjust = 100 - shares.reduce((s, n) => s + n, 0);
  if (shares.length > 0) shares[0] += shareAdjust;

  const cols = fallbackTargets.length;

  return (
    <div className="relative flex min-h-[560px] items-center justify-center overflow-hidden rounded-xl border border-border/60 bg-background/50 p-8">
      <div className="absolute right-4 top-4 z-20 flex items-center gap-2 text-xs text-muted-foreground">
        <span>Show Traffic %</span>
        <button
          type="button"
          onClick={() => setShowTraffic((visible) => !visible)}
          className={cn("relative inline-flex h-4 w-7 items-center rounded-full p-0.5 transition-colors", showTraffic ? "bg-primary/30" : "bg-muted")}
          aria-label={showTraffic ? "Hide traffic percentages" : "Show traffic percentages"}
          aria-pressed={showTraffic}
        >
          <span className={cn("h-3 w-3 rounded-full transition-transform", showTraffic ? "translate-x-3 bg-primary" : "bg-muted-foreground")} />
        </button>
      </div>

      <div className="flex w-full max-w-xl flex-col items-center" key={rule.name}>
        <div className="z-10 mb-6 flex flex-col items-center rounded-full border border-border bg-card/80 px-6 py-2 text-sm font-medium shadow-lg">
          <span className="text-foreground">Incoming Request <span className="ml-1 text-[10px] text-muted-foreground">User / Agent</span></span>
          <span className="mt-1 text-[10px] font-bold uppercase tracking-wider text-primary">Rule Triggered: {rule.name}</span>
        </div>

        <div className="relative h-8 w-px bg-primary/50">
          <span className="absolute -bottom-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 border-b-2 border-r-2 border-primary/50" />
        </div>

        <div className="z-10 flex flex-col items-center rounded-xl border-2 border-primary/30 bg-card px-8 py-4 shadow-[0_0_20px_color-mix(in_srgb,var(--primary)_15%,transparent)]">
          <Cpu className="mb-2 h-6 w-6 text-primary" />
          <p className="text-base font-bold text-foreground">Routing Engine</p>
          <p className="text-xs text-primary">Evaluate Rules</p>
        </div>

        <div className="relative mt-2 h-16 w-full">
          <svg className="absolute inset-0 h-full w-full" preserveAspectRatio="none" viewBox="0 0 100 100" aria-hidden>
            {fallbackTargets.map((_, index) => {
              const endX = cols <= 1 ? 50 : 10 + (80 * index) / (cols - 1);
              return (
                <path
                  key={index}
                  d={cols <= 1 ? "M50,0 L50,100" : `M50,0 Q50,50 ${endX},100`}
                  fill="none"
                  stroke="currentColor"
                  className="text-primary/70"
                  strokeWidth="1"
                  strokeDasharray={cols > 1 ? "4,4" : undefined}
                />
              );
            })}
          </svg>
        </div>

        <div className="relative z-10 mt-2 flex w-full justify-around">
          {fallbackTargets.map((target, index) => {
            const lane = laneForTarget(target.name, target.type);
            const isSecure = lane === "secure";
            return (
              <div key={`${target.name}-${index}`} className={cn("flex flex-col items-center", cols === 1 ? "scale-110" : "scale-95")}>
                {showTraffic && <span className={cn("mb-2 text-xs font-bold tabular-nums", lane === "cost" ? "text-emerald-600 dark:text-emerald-400" : lane === "secure" ? "text-violet-600 dark:text-violet-400" : "text-sky-600 dark:text-sky-400")}>{shares[index]}%</span>}
                <div className={cn("flex h-16 w-16 flex-col items-center justify-center rounded-xl border bg-card shadow-lg transition-colors", LANE_STYLES[lane].ring)}>
                  <span className={cn("mb-1 h-6 w-6 rounded-full", isSecure ? "border border-violet-500/30 bg-violet-500/10" : lane === "cost" ? "bg-emerald-500/20" : "bg-sky-500/20")}>
                    {isSecure ? <Shield className="m-1 h-4 w-4 text-violet-600 dark:text-violet-400" /> : <Cloud className={cn("m-1 h-4 w-4", lane === "cost" ? "text-emerald-600 dark:text-emerald-400" : "text-sky-600 dark:text-sky-400")} />}
                  </span>
                  <span className="line-clamp-2 px-1 text-center text-[10px] font-bold leading-tight text-foreground" title={target.name}>{target.name}</span>
                </div>
                <span className={cn("mt-1 text-[9px] font-medium", isSecure ? "rounded-sm border border-violet-500/30 bg-violet-500/10 px-1.5 text-violet-600 dark:text-violet-400" : "text-muted-foreground")}>
                  {isSecure ? "Air-Gapped" : providerLabel(target.type)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="absolute bottom-6 z-20 flex flex-wrap justify-center gap-x-6 gap-y-1 rounded-full border border-border bg-background/80 px-4 py-2 text-[10px] text-muted-foreground backdrop-blur-sm">
        <span className="flex items-center"><span className="mr-2 h-2 w-2 rounded-full bg-emerald-500" />Low Cost</span>
        <span className="flex items-center"><span className="mr-2 h-2 w-2 rounded-full bg-sky-500" />High Performance</span>
        <span className="flex items-center"><span className="mr-2 h-2 w-2 rounded-full bg-violet-500" />High Security (Air-Gapped)</span>
      </div>
    </div>
  );
}

// ─── mock chart data helpers (no API calls — purely presentational) ───────────

function buildPerfData(models: { model: string; latency: number; requests: number }[]) {
  const hours = ["9am", "10am", "11am", "12pm", "1pm", "2pm", "3pm", "4pm", "5pm"];
  return hours.map((hour) => {
    const row: Record<string, string | number> = { hour };
    models.forEach((m) => {
      row[m.model] = Math.max(50, m.latency + Math.floor((Math.random() - 0.5) * 40));
    });
    return row;
  });
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatRatePair(input = 0, output = 0): string {
  return `${formatUsd(input)} / ${formatUsd(output)}`;
}

// ─── main view ────────────────────────────────────────────────────────────────

export function LlmRouterView() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";
  const { models, rules, invalidateProviders, invalidateRules } = useLlmRouting();

  const [activeTab, setActiveTab] = useState<Tab>("rules");
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ApiRoutingModel | null>(null);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ApiRoutingRule | null>(null);
  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<ApiRoutingGroup | null>(null);
  const [groups, setGroups] = useState<ApiRoutingGroup[]>([]);
  const [clientApiKeys, setClientApiKeys] = useState<ApiClientApiKey[]>([]); // BL-088
  const [assignedKeyIds, setAssignedKeyIds] = useState<Set<string>>(new Set()); // BL-088: keys bound to selectedRule
  const [assignKeyModalOpen, setAssignKeyModalOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [rebalancing, setRebalancing] = useState(false);

  const activeModels = useMemo(() => models.filter((m) => m.isActive !== false), [models]);
  const totalRequests = activeModels.reduce((sum, m) => sum + m.requests, 0);

  const selectedRule = rules.find((r) => r.id === selectedRuleId) ?? rules[0] ?? null;

  // Auto-select first rule when rules load
  useEffect(() => {
    if (rules.length > 0 && !selectedRuleId) setSelectedRuleId(rules[0].id);
  }, [rules, selectedRuleId]);

  const fetchGroups = useMemo(
    () => async () => {
      if (!token) return;
      try {
        const data = await api.getRoutingGroups(token);
        setGroups(data || []);
      } catch (err) {
        console.warn("Failed to fetch routing groups:", err);
      }
    },
    [token]
  );

  // BL-088: load client API keys to show binding panel
  const fetchClientApiKeys = useMemo(
    () => async () => {
      if (!token) return;
      try {
        const data = await api.getClientApiKeys(token);
        setClientApiKeys(data || []);
      } catch {
        // non-fatal — panel shows empty state
      }
    },
    [token]
  );

  // BL-088: load keys assigned to the currently selected rule
  const fetchAssignedKeys = useMemo(
    () => async (ruleId: string) => {
      if (!token) return;
      try {
        const data = await api.getRoutingRuleClientKeys(token, ruleId);
        setAssignedKeyIds(new Set((data || []).map((k) => k.id)));
      } catch {
        setAssignedKeyIds(new Set());
      }
    },
    [token]
  );

  useEffect(() => { fetchGroups(); }, [fetchGroups]);
  useEffect(() => { fetchClientApiKeys(); }, [fetchClientApiKeys]);
  useEffect(() => {
    if (selectedRule) fetchAssignedKeys(selectedRule.id);
    else setAssignedKeyIds(new Set());
  }, [selectedRule, fetchAssignedKeys]);

  const perfData = useMemo(() => buildPerfData(activeModels), [activeModels]);
  const { data: costAnalytics } = useQuery({
    queryKey: ["cost-analytics", token],
    queryFn: () => api.getCostAnalytics(token!, 30),
    enabled: Boolean(token),
  });
  const costTrend = costAnalytics?.daily_trend ?? [];
  const totalSpend = costAnalytics?.summary.total_cost_usd ?? 0;
  const savedEstimate = useMemo(() => {
    const rows = costAnalytics?.by_model ?? [];
    if (!rows.length || !activeModels.length) return 0;
    const maxOut = Math.max(...activeModels.map((m) => m.costPer1mOutput ?? 0), 0);
    const maxIn = Math.max(...activeModels.map((m) => m.costPer1mInput ?? 0), 0);
    if (!maxIn && !maxOut) return 0;
    const atMax = rows.reduce((sum, row) => {
      return sum + ((row.prompt_tokens / 1_000_000) * maxIn + (row.completion_tokens / 1_000_000) * maxOut);
    }, 0);
    return Math.max(0, atMax - totalSpend);
  }, [activeModels, costAnalytics, totalSpend]);

  // ── handlers (unchanged) ──────────────────────────────────────────────────

  function openCreateModal() { setEditingProvider(null); setModalOpen(true); }
  function openEditModal(model: (typeof models)[0]) {
    if (!model.id) return;
    setEditingProvider({
      id: model.id, model: model.model, provider_type: model.providerType ?? "custom",
      endpoint_url: model.endpointUrl ?? null, requests: model.requests,
      percentage: model.percentage, latency: model.latency,
      success_rate: model.successRate, is_active: model.isActive !== false,
      api_key_set: model.apiKeySet, api_key_masked: model.apiKeyMasked,
      cost_per_1m_input: model.costPer1mInput ?? 0,
      cost_per_1m_output: model.costPer1mOutput ?? 0,
    });
    setModalOpen(true);
  }

  async function deleteProvider(model: (typeof models)[0]) {
    if (!token || !model.id) return;
    if (!window.confirm(`Delete ${model.model} from the model registry? This cannot be undone.`)) return;
    setActionError(null);
    try {
      await api.deleteLlmProvider(token, model.id);
      invalidateProviders();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to delete provider");
    }
  }

  function openCreateRuleModal() { setEditingRule(null); setRuleModalOpen(true); }
  function openEditRuleModal(rule: (typeof rules)[0]) {
    setEditingRule({
      id: rule.id, name: rule.name, priority: rule.priority,
      condition: rule.condition, target_model: rule.targetModel, status: rule.status,
      response_format: rule.responseFormat,
    });
    setRuleModalOpen(true);
  }

  async function deleteRule(rule: (typeof rules)[0]) {
    if (!token) return;
    if (!window.confirm(`Delete routing rule "${rule.name}"?`)) return;
    setActionError(null);
    try { await api.deleteRoutingRule(token, rule.id); invalidateRules(); }
    catch (err) { setActionError(err instanceof ApiError ? err.message : "Failed to delete routing rule"); }
  }

  function openCreateGroupModal() { setEditingGroup(null); setGroupModalOpen(true); }
  function openEditGroupModal(group: ApiRoutingGroup) { setEditingGroup(group); setGroupModalOpen(true); }

  async function deleteGroup(group: ApiRoutingGroup) {
    if (!token) return;
    if (!window.confirm(`Delete routing group "${group.name}"?`)) return;
    setActionError(null);
    try { await api.deleteRoutingGroup(token, group.id); fetchGroups(); }
    catch (err) { setActionError(err instanceof ApiError ? err.message : "Failed to delete routing group"); }
  }

  async function rebalanceFromTraffic() {
    if (!token) return;
    setActionError(null); setRebalancing(true);
    try { await api.rebalanceLlmProviders(token); invalidateProviders(); }
    catch (err) { setActionError(err instanceof ApiError ? err.message : "Failed to rebalance routing shares"); }
    finally { setRebalancing(false); }
  }

  // BL-088: persist unassign so it doesn't reappear after refresh
  async function unassignClientKey(key: ApiClientApiKey) {
    if (!token || !selectedRule) return;
    setActionError(null);
    try {
      await api.unassignRoutingRuleClientKey(token, selectedRule.id, key.id);
      fetchAssignedKeys(selectedRule.id);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to remove key assignment");
    }
  }

  const targetModelOptions = activeModels.map((m) => m.model);

  // ── render ──────────────────────────────────────────────────────────────────
  return (
    <div className="-m-4 flex min-h-full flex-col gap-0 bg-background p-4 text-foreground sm:-m-6 sm:p-6">
      {/* Top KPI strip */}
      <div className="grid gap-4 sm:grid-cols-3 mb-6">
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-xs text-muted-foreground mb-1">Total Routed</p>
            <p className="text-3xl font-bold">{formatNumber(totalRequests)}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-xs text-muted-foreground mb-1">Active Rules</p>
            <p className="text-3xl font-bold">{rules.filter((r) => r.status === "active").length}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-xs text-muted-foreground mb-1">Registered Providers</p>
            <p className="text-3xl font-bold">{activeModels.length}</p>
          </CardContent>
        </Card>
      </div>

      {actionError && <p className="mb-3 text-sm text-red-400">{actionError}</p>}

      <TabBar active={activeTab} onChange={setActiveTab} />

      {/* ── ROUTING RULES ────────────────────────────────────────────────────── */}
      {activeTab === "rules" && (
        <div className="grid gap-5 lg:grid-cols-12">
          <div className="rounded-xl border border-border/60 bg-card/50 lg:col-span-3">
            <div className="flex items-center justify-between border-b border-border/60 bg-muted/20 p-4">
              <h3 className="text-sm font-semibold text-foreground">Routing Rules ({rules.length})</h3>
              {canEdit && (
                <Button size="sm" className="h-8 gap-1.5 text-xs" onClick={openCreateRuleModal}>
                  <Plus className="h-3.5 w-3.5" /> Add rule
                </Button>
              )}
            </div>
            <div className="space-y-2 p-2">
              {rules.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border/60 py-10 text-center text-sm text-muted-foreground">
                  No routing rules configured
                </div>
              ) : (
                rules.map((rule) => (
                  <button
                    key={rule.id}
                    type="button"
                    onClick={() => setSelectedRuleId(rule.id)}
                    className={cn(
                      "w-full rounded-lg border p-3 text-left transition-all",
                      selectedRuleId === rule.id
                        ? "border-indigo-500/50 bg-indigo-500/10"
                        : "border-border/60 bg-card/50 hover:border-border/90"
                    )}
                  >
                    <div className="mb-1.5 flex items-start justify-between gap-2">
                      <span className={cn("text-sm font-semibold leading-tight", selectedRuleId === rule.id ? "text-primary" : "text-foreground")}>{rule.name}</span>
                      <Badge variant={rule.status === "active" ? "success" : "warning"} className="shrink-0 text-[10px]">
                        {rule.status}
                      </Badge>
                    </div>
                    <p className="truncate text-xs font-mono text-muted-foreground">{rule.condition}</p>
                    <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Zap className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">{rule.targetModel || "Default"}</span>
                      <span className="ml-auto shrink-0 rounded border border-border/60 bg-muted/30 px-1.5 py-0.5 text-[10px] tabular-nums">
                        P{rule.priority}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="lg:col-span-6">
            <h3 className="mb-3 text-sm font-semibold text-foreground">Visual Routing Engine</h3>
            <RoutingVisualEngine rule={selectedRule} models={activeModels} />
          </div>

          {selectedRule && (
            <Card className="border-border/60 bg-card/50 lg:col-span-3 lg:sticky lg:top-4 lg:max-h-[calc(100vh-10rem)] lg:overflow-y-auto">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="text-sm font-semibold">Rule Details</CardTitle>
                <div className="flex gap-2">
                  {canEdit && (
                    <>
                      <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs" onClick={() => openEditRuleModal(selectedRule)}>
                        <Pencil className="h-3.5 w-3.5" /> Edit Rule
                      </Button>
                      <Button
                        size="sm" variant="ghost"
                        className="h-8 w-8 p-0 text-red-400 hover:text-red-300"
                        onClick={() => deleteRule(selectedRule)}
                        aria-label="Delete rule"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2 text-sm font-medium text-primary">
                  {selectedRule.name}
                </div>

                <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                  <p className="mb-2 text-[11px] uppercase tracking-[0.12em] text-muted-foreground">Condition (CEL)</p>
                  <code className="block break-all text-sm font-mono leading-relaxed text-foreground">
                    {selectedRule.condition || "— no condition —"}
                  </code>
                </div>

                <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                  <p className="mb-2 text-[11px] uppercase tracking-[0.12em] text-muted-foreground">Universal Gateway Config</p>
                  <div className="mb-3 flex items-start justify-between gap-3 text-sm">
                    <span className="text-muted-foreground">Target Model(s)</span>
                    <div className="flex flex-wrap justify-end gap-1.5">
                      {(selectedRule.targetModel || "").split(",").map((m) => m.trim()).filter(Boolean).map((m) => {
                        const found = activeModels.find((am) => am.model === m);
                        return (
                          <span key={m} className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-card px-2 py-1 text-xs font-medium">
                            <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: found?.color ?? "#6366f1" }} />
                            {m}
                          </span>
                        );
                      })}
                      {!selectedRule.targetModel && <span className="text-xs text-muted-foreground">Default pool</span>}
                    </div>
                  </div>
                  <div className="mb-2 text-sm text-muted-foreground">Client Response Format (Translation)</div>
                  <span className="inline-flex items-center gap-1 rounded-md border border-primary/30 bg-primary/5 px-2 py-1 text-xs font-mono text-primary">
                    {selectedRule.responseFormat ?? "auto"}
                  </span>
                  <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                    The gateway automatically translates upstream execution into this specified schema for transparent client compatibility.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="mb-1.5 text-xs text-muted-foreground">Priority</p>
                    <p className="text-sm font-semibold">{selectedRule.priority}</p>
                  </div>
                  <div>
                    <p className="mb-1.5 text-xs text-muted-foreground">Status</p>
                    <Badge variant={selectedRule.status === "active" ? "success" : "warning"}>{selectedRule.status}</Badge>
                  </div>
                </div>

                {/* BL-088: API key binding panel */}
                <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <p className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                      <Zap className="h-3.5 w-3.5 text-primary" />
                      Assigned API Keys / Clients
                    </p>
                    <Button type="button" size="sm" variant="outline" className="h-7 gap-1.5 text-[10px]" onClick={() => setAssignKeyModalOpen(true)}>
                      <Plus className="h-3 w-3" /> Assign key
                    </Button>
                  </div>
                  {(() => {
                    const assignedKeys = clientApiKeys.filter((k) => assignedKeyIds.has(k.id));
                    if (assignedKeys.length === 0) {
                      return (
                        <p className="text-xs text-muted-foreground">
                          No client API keys assigned yet. Click <span className="font-medium">Assign key</span> to bind one.
                        </p>
                      );
                    }
                    return (
                      <div className="space-y-2">
                        {assignedKeys.map((k) => (
                          <div key={k.id} className="flex items-center justify-between gap-2 rounded-md border border-border/50 bg-card/60 px-3 py-2">
                            <div className="min-w-0">
                              <p className="truncate text-xs font-medium">{k.name}</p>
                              <p className="truncate font-mono text-[11px] text-muted-foreground">{k.key_masked}</p>
                            </div>
                            <div className="flex shrink-0 items-center gap-2">
                              {k.bundle_name && <span className="text-[10px] text-muted-foreground">bundle: {k.bundle_name}</span>}
                              <Badge variant={k.is_active ? "success" : "outline"} className="text-[10px]">
                                {k.is_active ? "active" : "inactive"}
                              </Badge>
                              <Button
                                type="button" size="sm" variant="ghost"
                                className="h-7 w-7 p-0 text-muted-foreground hover:text-red-400"
                                onClick={() => unassignClientKey(k)}
                                aria-label={`Remove ${k.name}`}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── MODEL REGISTRY ───────────────────────────────────────────────────── */}
      {activeTab === "models" && (
        <div className="grid gap-5 lg:grid-cols-12">
          {/* Donut */}
          <Card className="lg:col-span-4 border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle className="text-sm">Routing Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={activeModels}
                      dataKey="requests"
                      nameKey="model"
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={2}
                      stroke="none"
                    >
                      {activeModels.map((entry) => (
                        <Cell key={entry.model} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      formatter={(value) => formatNumber(Number(value))}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <p className="text-2xl font-bold">{formatNumber(totalRequests)}</p>
                  <p className="text-xs text-muted-foreground">requests</p>
                </div>
              </div>
              <div className="mt-3 space-y-1.5">
                {activeModels.map((m) => (
                  <div key={m.model} className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: m.color }} />
                      {m.model}
                    </span>
                    <span className="text-muted-foreground tabular-nums">{m.percentage}%</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Model table */}
          <Card className="lg:col-span-8 border-border/60 bg-card/50">
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
              <CardTitle className="text-sm">Model Performance</CardTitle>
              {canEdit && (
                <div className="flex gap-2">
                  <Button
                    size="sm" variant="outline" className="gap-1.5"
                    disabled={rebalancing || totalRequests === 0}
                    onClick={rebalanceFromTraffic}
                  >
                    <RefreshCw className={cn("h-4 w-4", rebalancing && "animate-spin")} />
                    {rebalancing ? "Rebalancing…" : "Rebalance"}
                  </Button>
                  <Button size="sm" className="gap-1.5" onClick={openCreateModal}>
                    <Plus className="h-4 w-4" /> Register provider
                  </Button>
                </div>
              )}
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/60">
                    <th className="pb-3 text-left text-xs font-medium text-muted-foreground">Model</th>
                    <th className="pb-3 text-left text-xs font-medium text-muted-foreground">Type</th>
                    <th className="pb-3 text-right text-xs font-medium text-muted-foreground">Requests</th>
                    <th className="pb-3 text-right text-xs font-medium text-muted-foreground">Share</th>
                    <th className="pb-3 text-right text-xs font-medium text-muted-foreground">Est. Cost (1M In/Out)</th>
                    <th className="pb-3 text-right text-xs font-medium text-muted-foreground">Latency</th>
                    <th className="pb-3 text-right text-xs font-medium text-muted-foreground">Success</th>
                    {canEdit && <th className="pb-3 text-right text-xs font-medium text-muted-foreground">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {models.map((row) => {
                    const isLocal = row.providerType === "ollama" || row.providerType === "custom";
                    return (
                      <tr key={row.id ?? row.model} className="hover:bg-muted/30 transition-colors">
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <div className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: row.color }} />
                            <span className="font-medium">{row.model}</span>
                            {row.isActive === false && (
                              <Badge variant="outline" className="text-[10px]">inactive</Badge>
                            )}
                          </div>
                        </td>
                        <td className="py-3">
                          <span className="flex items-center gap-1.5 text-xs text-muted-foreground capitalize">
                            {isLocal ? <Cpu className="h-3.5 w-3.5" /> : <Cloud className="h-3.5 w-3.5" />}
                            {row.providerType ?? "—"}
                          </span>
                        </td>
                        <td className="py-3 text-right tabular-nums">{formatNumber(row.requests)}</td>
                        <td className="py-3 text-right tabular-nums">{row.percentage}%</td>
                        <td className="py-3 text-right tabular-nums text-xs">
                          {formatRatePair(row.costPer1mInput, row.costPer1mOutput)}
                        </td>
                        <td className="py-3 text-right tabular-nums">{row.latency}ms</td>
                        <td className="py-3 text-right text-emerald-400 tabular-nums">{row.successRate}%</td>
                        {canEdit && (
                          <td className="py-3">
                            <div className="flex justify-end gap-1">
                              <Button
                                variant="ghost" size="sm"
                                className="h-8 w-8 p-0"
                                disabled={!row.id}
                                onClick={() => openEditModal(row)}
                                aria-label={`Edit ${row.model}`}
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="ghost" size="sm"
                                className="h-8 w-8 p-0 text-red-400 hover:text-red-300"
                                disabled={!row.id}
                                onClick={() => deleteProvider(row)}
                                aria-label={`Delete ${row.model}`}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {canEdit && (
                <p className="mt-3 text-xs text-muted-foreground">
                  Routing share (%) controls weighted distribution when{" "}
                  <code className="text-[11px]">model: auto</code> and no active rule matches.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── ROUTING GROUPS ───────────────────────────────────────────────────── */}
      {activeTab === "groups" && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle>LLM Routing Groups</CardTitle>
              <p className="text-xs text-muted-foreground mt-1">
                Virtual model groups (e.g.{" "}
                <code className="text-[11px]">model: &quot;production&quot;</code>) with weighted pools &amp; auto-failover
              </p>
            </div>
            {canEdit && (
              <Button size="sm" className="gap-1.5" onClick={openCreateGroupModal}>
                <Plus className="h-4 w-4" /> Create Group
              </Button>
            )}
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/60">
                  <th className="pb-3 text-left text-xs font-medium text-muted-foreground">Group Alias</th>
                  <th className="pb-3 text-left text-xs font-medium text-muted-foreground">Strategy</th>
                  <th className="pb-3 text-left text-xs font-medium text-muted-foreground">Member Models</th>
                  <th className="pb-3 text-left text-xs font-medium text-muted-foreground">Status</th>
                  {canEdit && <th className="pb-3 text-right text-xs font-medium text-muted-foreground">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {groups.length === 0 ? (
                  <tr>
                    <td colSpan={canEdit ? 5 : 4} className="py-10 text-center text-sm text-muted-foreground">
                      No routing groups configured. Create a virtual model alias for weighted pools or auto-failover.
                    </td>
                  </tr>
                ) : (
                  groups.map((grp) => (
                    <tr key={grp.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 font-medium">
                        <div>
                          <span>{grp.name}</span>
                          {grp.description && <p className="text-xs font-normal text-muted-foreground">{grp.description}</p>}
                        </div>
                      </td>
                      <td className="py-3">
                        <Badge variant="outline" className="capitalize text-xs">{grp.strategy}</Badge>
                      </td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-1">
                          {grp.members?.map((m, idx) => (
                            <Badge key={idx} variant="secondary" className="text-[11px] font-mono">
                              {m.model} {grp.strategy === "failover" ? `#${m.priority}` : `${m.weight}%`}
                            </Badge>
                          ))}
                        </div>
                      </td>
                      <td className="py-3">
                        <Badge variant={grp.status === "active" ? "success" : "warning"}>{grp.status}</Badge>
                      </td>
                      {canEdit && (
                        <td className="py-3">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost" size="sm" className="h-8 w-8 p-0"
                              onClick={() => openEditGroupModal(grp)}
                              aria-label={`Edit ${grp.name}`}
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost" size="sm"
                              className="h-8 w-8 p-0 text-red-400 hover:text-red-300"
                              onClick={() => deleteGroup(grp)}
                              aria-label={`Delete ${grp.name}`}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* ── PERFORMANCE ──────────────────────────────────────────────────────── */}
      {activeTab === "performance" && (
        <div className="grid gap-5 lg:grid-cols-2">
          {/* Latency chart */}
          <Card className="border-border/60 bg-card/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Request Latency by Model</CardTitle>
              <p className="text-xs text-muted-foreground">Average ms over the last 9 hours</p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={perfData} margin={{ top: 4, right: 8, bottom: 4, left: -24 }}>
                  <XAxis dataKey="hour" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} unit="ms" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(v) => [`${v}ms`]}
                  />
                  {activeModels.map((m) => (
                    <Area
                      key={m.model}
                      type="monotone"
                      dataKey={m.model}
                      stroke={m.color}
                      fill={m.color + "18"}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
              {/* Legend */}
              <div className="mt-2 flex flex-wrap gap-3">
                {activeModels.map((m) => (
                  <span key={m.model} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: m.color }} />
                    {m.model}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Throughput chart */}
          <Card className="border-border/60 bg-card/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Request Throughput</CardTitle>
              <p className="text-xs text-muted-foreground">Requests per model in the current period</p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={activeModels} margin={{ top: 4, right: 8, bottom: 4, left: -24 }}>
                  <XAxis dataKey="model" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                    formatter={(v) => [formatNumber(Number(v)), "requests"]}
                  />
                  <Bar dataKey="requests" radius={[6, 6, 0, 0]}>
                    {activeModels.map((m) => (
                      <Cell key={m.model} fill={m.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Per-model stat cards */}
          {activeModels.map((m) => (
            <Card key={m.model} className="border-border/60 bg-card/50">
              <CardContent className="p-5 flex gap-5 items-start">
                <div className="w-2 self-stretch rounded-full shrink-0" style={{ backgroundColor: m.color }} />
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-start mb-3">
                    <p className="font-semibold truncate">{m.model}</p>
                    <span className="flex items-center gap-1 text-xs text-muted-foreground border border-border/60 rounded px-1.5 py-0.5 bg-muted/30">
                      {(m.providerType === "ollama" || m.providerType === "custom")
                        ? <><Cpu className="h-3 w-3" /> Air-Gapped</>
                        : <><Cloud className="h-3 w-3" /> Cloud</>}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div><p className="text-xs text-muted-foreground">Latency</p><p className="font-bold">{m.latency}ms</p></div>
                    <div><p className="text-xs text-muted-foreground">Success</p><p className="font-bold text-emerald-400">{m.successRate}%</p></div>
                    <div><p className="text-xs text-muted-foreground">Share</p><p className="font-bold">{m.percentage}%</p></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* ── COST ─────────────────────────────────────────────────────────────── */}
      {activeTab === "cost" && (
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-3">
            <Card className="border-border/60 bg-card/50">
              <CardContent className="p-5">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                  <p className="text-xs text-muted-foreground">Total spend (30d)</p>
                </div>
                <p className="text-3xl font-bold">{formatUsd(totalSpend)}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  From registry 1M in/out rates × gateway tokens
                </p>
              </CardContent>
            </Card>
            <Card className="border-border/60 bg-card/50">
              <CardContent className="p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-emerald-400" />
                  <p className="text-xs text-muted-foreground">Est. savings vs highest rate</p>
                </div>
                <p className="text-3xl font-bold text-emerald-400">{formatUsd(savedEstimate)}</p>
              </CardContent>
            </Card>
            <Card className="border-border/60 bg-card/50">
              <CardContent className="p-5">
                <div className="flex items-center gap-2 mb-2">
                  <p className="text-xs text-muted-foreground">Tokens (30d)</p>
                </div>
                <p className="text-3xl font-bold">
                  {formatNumber(costAnalytics?.summary.total_tokens ?? 0)}
                </p>
              </CardContent>
            </Card>
          </div>

          <Card className="border-border/60 bg-card/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Spend by model</CardTitle>
              <p className="text-xs text-muted-foreground">
                Cost = (input tokens × in rate + output tokens × out rate) / 1M
              </p>
            </CardHeader>
            <CardContent>
              {(costAnalytics?.by_model.length ?? 0) === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No attributed LLM traffic yet. Set Est. Cost on models in the registry, then send gateway traffic.
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border/60 text-xs text-muted-foreground">
                      <th className="pb-2 text-left font-medium">Model</th>
                      <th className="pb-2 text-right font-medium">1M In/Out</th>
                      <th className="pb-2 text-right font-medium">Input tokens</th>
                      <th className="pb-2 text-right font-medium">Output tokens</th>
                      <th className="pb-2 text-right font-medium">Spend</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {costAnalytics!.by_model.map((row) => {
                      const registry = activeModels.find(
                        (m) => m.model.toLowerCase() === row.label.toLowerCase()
                      );
                      return (
                        <tr key={row.key}>
                          <td className="py-2 font-medium">{row.label}</td>
                          <td className="py-2 text-right tabular-nums text-xs">
                            {formatRatePair(registry?.costPer1mInput, registry?.costPer1mOutput)}
                          </td>
                          <td className="py-2 text-right tabular-nums">{formatNumber(row.prompt_tokens)}</td>
                          <td className="py-2 text-right tabular-nums">{formatNumber(row.completion_tokens)}</td>
                          <td className="py-2 text-right tabular-nums">{formatUsd(row.cost_usd)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/60 bg-card/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Daily spend (30 days)</CardTitle>
            </CardHeader>
            <CardContent>
              {costTrend.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">No daily spend yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={costTrend} margin={{ top: 4, right: 8, bottom: 4, left: -24 }}>
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                      interval={4}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v) => `$${v}`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      formatter={(v) => [formatUsd(Number(v)), "Spend"]}
                    />
                    <Area type="monotone" dataKey="cost_usd" stroke="#6366f1" fill="#6366f118" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Modals — all props unchanged */}
      <LlmProviderModal
        open={modalOpen}
        provider={editingProvider}
        token={token}
        onClose={() => setModalOpen(false)}
        onSaved={invalidateProviders}
      />
      <RoutingRuleModal
        open={ruleModalOpen}
        rule={editingRule}
        targetModels={targetModelOptions}
        token={token}
        onClose={() => setRuleModalOpen(false)}
        onSaved={invalidateRules}
      />
      <RoutingGroupModal
        open={groupModalOpen}
        group={editingGroup}
        token={token}
        onClose={() => setGroupModalOpen(false)}
        onSaved={fetchGroups}
      />
      <AssignClientKeyModal
        open={assignKeyModalOpen}
        rule={selectedRule}
        clientApiKeys={clientApiKeys}
        assignedKeyIds={assignedKeyIds}
        token={token}
        onClose={() => setAssignKeyModalOpen(false)}
        onAssigned={() => selectedRule && fetchAssignedKeys(selectedRule.id)}
      />
    </div>
  );
}
