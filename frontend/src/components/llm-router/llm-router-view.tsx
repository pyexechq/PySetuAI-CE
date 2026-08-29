"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Pencil, Plus, RefreshCw, Trash2, Cpu, Cloud, Zap, DollarSign, Shield,
  Layers, ArrowRightLeft, Sparkles, CheckCircle2, TrendingDown, Activity, KeyRound,
  Check, Copy, Terminal, Server
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LlmProviderModal } from "@/components/llm-router/llm-provider-modal";
import { RoutingRuleModal } from "@/components/llm-router/routing-rule-modal";
import { RoutingGroupModal } from "@/components/llm-router/routing-group-modal";
import { AssignClientKeyModal } from "@/components/llm-router/assign-client-key-modal";
import { UagAdminPanel } from "@/components/compatibility-center/uag-admin-panel";
import { useLlmRouting } from "@/hooks/use-llm-routing";
import { api, ApiError, type ApiRoutingModel, type ApiRoutingRule, type ApiRoutingGroup, type ApiClientApiKey } from "@/lib/api";
import { formatNumber, cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

// ─── types ────────────────────────────────────────────────────────────────────

type Tab = "rules" | "models" | "groups" | "gateway" | "performance" | "cost";

const TABS: { id: Tab; label: string }[] = [
  { id: "rules", label: "Routing Rules & Canvas" },
  { id: "models", label: "Model Registry" },
  { id: "groups", label: "Routing Groups" },
  { id: "gateway", label: "Gateway & Aliases" },
  { id: "performance", label: "Latency & SLA" },
  { id: "cost", label: "Cost Arbitrage ROI" },
];

const TAB_IDS = new Set<string>(TABS.map((tab) => tab.id));

function parseTabParam(value: string | null): Tab | null {
  if (!value || !TAB_IDS.has(value)) return null;
  return value as Tab;
}

// ─── TabBar ───────────────────────────────────────────────────────────────────

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <div className="flex items-center gap-1.5 overflow-x-auto p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs mb-6">
      {TABS.map((tab) => (
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

// ─── RoutingVisualEngine ─────────────────────────────────────────────────────

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
  cost: { dot: "bg-emerald-500", ring: "ring-emerald-500/40 border-emerald-500/30", label: "Cost Arbitrage" },
  perf: { dot: "bg-sky-500", ring: "ring-sky-500/40 border-sky-500/30", label: "High Performance" },
  secure: { dot: "bg-violet-500", ring: "ring-violet-500/40 border-violet-500/30", label: "Air-Gapped / Private" },
};

function providerLabel(type: string): string {
  const t = (type || "").toLowerCase();
  if (t === "openai") return "OpenAI";
  if (t === "anthropic") return "Anthropic";
  if (t === "gemini") return "Google Gemini";
  if (t === "ollama") return "Air-Gapped Ollama";
  if (t === "bedrock") return "AWS Bedrock";
  if (t === "vertex") return "GCP Vertex";
  return type || "Cloud Provider";
}

function RoutingVisualEngine({ rule, models }: RoutingVisualEngineProps) {
  const [showTraffic, setShowTraffic] = useState(true);

  if (!rule) {
    return (
      <div className="flex h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-border/80 bg-card/40 p-6 text-center text-sm text-muted-foreground">
        <ArrowRightLeft className="h-8 w-8 text-muted-foreground/50 mb-2" />
        <p className="font-semibold text-foreground">Select a routing rule to view execution flow</p>
        <p className="text-xs text-muted-foreground mt-1 max-w-sm">
          The canvas dynamically visualizes prompt condition matching, CEL evaluation, and upstream model multiplexing.
        </p>
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
    <div className="relative flex min-h-[580px] items-center justify-center overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-b from-card/90 via-card/50 to-muted/20 p-8 shadow-sm">
      {/* Top Toggle */}
      <div className="absolute right-4 top-4 z-20 flex items-center gap-2 text-xs text-muted-foreground bg-card/80 px-3 py-1.5 rounded-full border border-border/60 backdrop-blur-sm shadow-xs">
        <span className="font-medium">Traffic Weights</span>
        <button
          type="button"
          onClick={() => setShowTraffic((visible) => !visible)}
          className={cn("relative inline-flex h-4 w-7 items-center rounded-full p-0.5 transition-colors", showTraffic ? "bg-primary" : "bg-muted")}
          aria-label={showTraffic ? "Hide traffic percentages" : "Show traffic percentages"}
          aria-pressed={showTraffic}
        >
          <span className={cn("h-3 w-3 rounded-full bg-white transition-transform", showTraffic ? "translate-x-3" : "translate-x-0")} />
        </button>
      </div>

      <div className="flex w-full max-w-xl flex-col items-center" key={rule.name}>
        {/* Step 1: Ingress */}
        <div className="z-10 mb-6 flex flex-col items-center rounded-2xl border border-border/80 bg-card px-6 py-3 text-sm font-medium shadow-md">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-bold text-foreground">Client Ingress Request</span>
            <Badge variant="outline" className="text-[10px] py-0 px-1.5 font-mono bg-muted">REST / SDK</Badge>
          </div>
          <span className="mt-1 text-[11px] font-bold text-primary">Active Rule: {rule.name}</span>
        </div>

        {/* Arrow Down */}
        <div className="relative h-8 w-px bg-primary/60">
          <span className="absolute -bottom-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 border-b-2 border-r-2 border-primary/60" />
        </div>

        {/* Step 2: Routing Engine Core */}
        <div className="z-10 flex flex-col items-center rounded-2xl border-2 border-primary/40 bg-card px-8 py-4 shadow-lg shadow-primary/10">
          <div className="h-9 w-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-1.5">
            <Cpu className="h-5 w-5" />
          </div>
          <p className="text-sm font-bold text-foreground">Dynamic Routing Engine</p>
          <p className="text-[11px] text-primary font-mono font-medium mt-0.5">CEL & Intent Evaluation (&lt;0.5ms)</p>
        </div>

        {/* SVG Routing Fan-out */}
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
                  strokeWidth="1.5"
                  strokeDasharray={cols > 1 ? "4,4" : undefined}
                />
              );
            })}
          </svg>
        </div>

        {/* Step 3: Upstream Target Pools */}
        <div className="relative z-10 mt-2 flex w-full justify-around gap-2">
          {fallbackTargets.map((target, index) => {
            const lane = laneForTarget(target.name, target.type);
            const isSecure = lane === "secure";
            return (
              <div key={`${target.name}-${index}`} className={cn("flex flex-col items-center", cols === 1 ? "scale-105" : "scale-95")}>
                {showTraffic && (
                  <span className={cn("mb-2 text-xs font-bold tabular-nums px-2 py-0.5 rounded-full border shadow-xs",
                    lane === "cost"
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                      : isSecure
                      ? "bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/30"
                      : "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/30"
                  )}>
                    {shares[index]}%
                  </span>
                )}
                <div className={cn("flex h-20 w-20 flex-col items-center justify-center rounded-2xl border bg-card p-2 shadow-md transition-all hover:scale-105", LANE_STYLES[lane].ring)}>
                  <span className={cn("mb-1 h-7 w-7 rounded-xl flex items-center justify-center",
                    isSecure ? "bg-violet-500/10 text-violet-500" : lane === "cost" ? "bg-emerald-500/10 text-emerald-500" : "bg-sky-500/10 text-sky-500"
                  )}>
                    {isSecure ? <Shield className="h-4 w-4" /> : <Cloud className="h-4 w-4" />}
                  </span>
                  <span className="line-clamp-2 px-1 text-center text-[10px] font-bold leading-tight text-foreground" title={target.name}>
                    {target.name}
                  </span>
                </div>
                <span className={cn("mt-1.5 text-[9px] font-semibold px-2 py-0.5 rounded-full border",
                  isSecure ? "border-violet-500/30 bg-violet-500/10 text-violet-600 dark:text-violet-400" : "border-border/60 bg-muted/40 text-muted-foreground"
                )}>
                  {isSecure ? "Air-Gapped" : providerLabel(target.type)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend Footer */}
      <div className="absolute bottom-4 z-20 flex flex-wrap justify-center gap-x-6 gap-y-1 rounded-full border border-border/80 bg-background/80 px-4 py-1.5 text-[10px] text-muted-foreground backdrop-blur-sm shadow-xs">
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald-500" />Low Cost</span>
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-sky-500" />High Performance</span>
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-violet-500" />Air-Gapped / Private</span>
      </div>
    </div>
  );
}

// ─── helpers ──────────────────────────────────────────────────────────────────

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
  const router = useRouter();
  const searchParams = useSearchParams();
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";
  const { models, rules, invalidateProviders, invalidateRules } = useLlmRouting();

  const [activeTab, setActiveTab] = useState<Tab>(() => parseTabParam(searchParams.get("tab")) ?? "rules");
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ApiRoutingModel | null>(null);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ApiRoutingRule | null>(null);
  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<ApiRoutingGroup | null>(null);
  const [groups, setGroups] = useState<ApiRoutingGroup[]>([]);
  const [clientApiKeys, setClientApiKeys] = useState<ApiClientApiKey[]>([]);
  const [assignedKeyIds, setAssignedKeyIds] = useState<Set<string>>(new Set());
  const [assignKeyModalOpen, setAssignKeyModalOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [rebalancing, setRebalancing] = useState(false);

  const activeModels = useMemo(() => models.filter((m) => m.isActive !== false), [models]);
  const totalRequests = activeModels.reduce((sum, m) => sum + m.requests, 0);
  const targetModelOptions = activeModels.map((m) => m.model);

  const selectedRule = rules.find((r) => r.id === selectedRuleId) ?? rules[0] ?? null;

  useEffect(() => {
    if (rules.length > 0 && !selectedRuleId) setSelectedRuleId(rules[0].id);
  }, [rules, selectedRuleId]);

  useEffect(() => {
    const tab = parseTabParam(searchParams.get("tab"));
    if (tab) setActiveTab(tab);
  }, [searchParams]);

  function handleTabChange(tab: Tab) {
    setActiveTab(tab);
    router.replace(`/llm-router?tab=${tab}`, { scroll: false });
  }

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

  const fetchClientApiKeys = useMemo(
    () => async () => {
      if (!token) return;
      try {
        const data = await api.getClientApiKeys(token);
        setClientApiKeys(data || []);
      } catch {
        // non-fatal
      }
    },
    [token]
  );

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
      model_aliases: model.modelAliases ?? [],
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

  return (
    <div className="space-y-6">
      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2.5 max-w-xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Dynamic Routing Active
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <TrendingDown className="h-3.5 w-3.5 text-emerald-500" />
                Up to 94% Cost Arbitrage
              </Badge>
              <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-xs font-mono">
                CEL Evaluator &lt;0.5ms
              </Badge>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              Universal LLM Router & Fallback Multiplexer
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Intent-driven model selection, automated cost arbitrage, and zero-downtime failover across registered OpenAI, Anthropic, Gemini, Bedrock, and Ollama pools.
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-3 shrink-0">
            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Total Routed</span>
                <ArrowRightLeft className="h-3.5 w-3.5 text-primary" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-foreground">{formatNumber(totalRequests)}</p>
              <p className="text-[10px] text-muted-foreground">Requests steered</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Active Rules</span>
                <Zap className="h-3.5 w-3.5 text-amber-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-foreground">{rules.filter((r) => r.status === "active").length}</p>
              <p className="text-[10px] text-muted-foreground">In policy evaluation</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Model Pools</span>
                <Cloud className="h-3.5 w-3.5 text-cyan-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-foreground">{activeModels.length}</p>
              <p className="text-[10px] text-muted-foreground">Upstreams connected</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Savings ROI</span>
                <DollarSign className="h-3.5 w-3.5 text-emerald-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-emerald-600 dark:text-emerald-400">{formatUsd(savedEstimate)}</p>
              <p className="text-[10px] text-muted-foreground">Estimated savings</p>
            </div>
          </div>
        </div>
      </div>

      {actionError && (
        <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400 text-xs font-medium">
          {actionError}
        </div>
      )}

      {/* ─── Navigation Tabs ──────────────────────────────────────────────────── */}
      <TabBar active={activeTab} onChange={handleTabChange} />

      {/* ── TAB 1: Routing Rules & Canvas ──────────────────────────────────────── */}
      {activeTab === "rules" && (
        <div className="grid gap-5 lg:grid-cols-12">
          {/* Rules Roster */}
          <div className="rounded-2xl border border-border/80 bg-card/60 shadow-xs lg:col-span-3 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-border/60 bg-muted/20 p-4 rounded-t-2xl">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Routing Rules ({rules.length})
                  </h3>
                  <p className="text-[10px] text-muted-foreground">Prioritized evaluation order</p>
                </div>
                {canEdit && (
                  <Button size="sm" className="h-7 gap-1 text-xs" onClick={openCreateRuleModal}>
                    <Plus className="h-3.5 w-3.5" /> Add Rule
                  </Button>
                )}
              </div>

              <div className="space-y-2 p-3">
                {rules.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-border/60 py-10 text-center text-xs text-muted-foreground">
                    No routing rules configured
                  </div>
                ) : (
                  rules.map((rule) => (
                    <button
                      key={rule.id}
                      type="button"
                      onClick={() => setSelectedRuleId(rule.id)}
                      className={cn(
                        "w-full rounded-xl border p-3 text-left transition-all",
                        selectedRuleId === rule.id
                          ? "border-primary bg-primary/10 shadow-xs font-medium"
                          : "border-border/60 bg-card/70 hover:border-border/90"
                      )}
                    >
                      <div className="mb-1.5 flex items-start justify-between gap-2">
                        <span className={cn("text-xs font-bold leading-tight", selectedRuleId === rule.id ? "text-primary" : "text-foreground")}>
                          {rule.name}
                        </span>
                        <Badge variant={rule.status === "active" ? "success" : "warning"} className="shrink-0 text-[9px] py-0 px-1 font-mono">
                          {rule.status}
                        </Badge>
                      </div>
                      <p className="truncate text-[11px] font-mono text-muted-foreground">{rule.condition || "Default rule"}</p>
                      <div className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                        <Zap className="h-3 w-3 shrink-0 text-primary" />
                        <span className="truncate">{rule.targetModel || "Default"}</span>
                        <span className="ml-auto shrink-0 rounded border border-border/60 bg-muted/40 px-1.5 py-0.5 text-[9px] font-mono font-bold tabular-nums">
                          P{rule.priority}
                        </span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Visual Routing Canvas */}
          <div className="lg:col-span-6 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5 text-primary" />
                Live Visual Routing Canvas
              </h3>
              <span className="text-[11px] text-muted-foreground">Interactive packet simulation</span>
            </div>
            <RoutingVisualEngine rule={selectedRule} models={activeModels} />
          </div>

          {/* Rule Details Sidebar */}
          {selectedRule && (
            <Card className="border-border/80 bg-card/60 shadow-xs lg:col-span-3 lg:sticky lg:top-4 lg:max-h-[calc(100vh-10rem)] lg:overflow-y-auto rounded-2xl">
              <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/60">
                <CardTitle className="text-xs font-bold uppercase tracking-wider text-foreground">Rule Inspector</CardTitle>
                <div className="flex gap-1.5">
                  {canEdit && (
                    <>
                      <Button size="sm" variant="outline" className="h-7 gap-1 text-xs" onClick={() => openEditRuleModal(selectedRule)}>
                        <Pencil className="h-3 w-3" /> Edit
                      </Button>
                      <Button
                        size="sm" variant="ghost"
                        className="h-7 w-7 p-0 text-red-500 hover:text-red-400"
                        onClick={() => deleteRule(selectedRule)}
                        aria-label="Delete rule"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </>
                  )}
                </div>
              </CardHeader>

              <CardContent className="space-y-4 pt-4 text-xs">
                <div className="rounded-xl border border-border/60 bg-muted/20 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono mb-1">Rule Name</p>
                  <p className="font-bold text-foreground text-sm">{selectedRule.name}</p>
                </div>

                <div className="rounded-xl border border-border/60 bg-muted/20 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono mb-1">CEL Condition</p>
                  <code className="block break-all font-mono text-[11px] text-foreground leading-relaxed">
                    {selectedRule.condition || "— evaluates true for all requests —"}
                  </code>
                </div>

                <div className="rounded-xl border border-border/60 bg-muted/20 p-3 space-y-2">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">Target Pool & Schema</p>
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-muted-foreground">Target Model(s):</span>
                    <span className="font-semibold text-foreground truncate">{selectedRule.targetModel || "Default Pool"}</span>
                  </div>
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-muted-foreground">Response Format:</span>
                    <Badge variant="outline" className="text-[10px] font-mono text-primary border-primary/30">
                      {selectedRule.responseFormat ?? "auto-translate"}
                    </Badge>
                  </div>
                </div>

                {/* API Key Binding */}
                <div className="rounded-xl border border-border/60 bg-muted/20 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono flex items-center gap-1">
                      <KeyRound className="h-3 w-3 text-primary" />
                      Bound Client Keys
                    </p>
                    <Button type="button" size="sm" variant="outline" className="h-6 text-[10px] gap-1 px-2" onClick={() => setAssignKeyModalOpen(true)}>
                      <Plus className="h-2.5 w-2.5" /> Bind
                    </Button>
                  </div>
                  {(() => {
                    const assignedKeys = clientApiKeys.filter((k) => assignedKeyIds.has(k.id));
                    if (assignedKeys.length === 0) {
                      return (
                        <p className="text-[11px] text-muted-foreground">
                          No dedicated client keys bound to this rule.
                        </p>
                      );
                    }
                    return (
                      <div className="space-y-1.5 pt-1">
                        {assignedKeys.map((k) => (
                          <div key={k.id} className="flex items-center justify-between gap-1.5 rounded-lg border border-border/50 bg-card p-2">
                            <div className="min-w-0">
                              <p className="truncate font-semibold text-[11px]">{k.name}</p>
                              <p className="truncate font-mono text-[10px] text-muted-foreground">{k.key_masked}</p>
                            </div>
                            <Button
                              type="button" size="sm" variant="ghost"
                              className="h-6 w-6 p-0 text-muted-foreground hover:text-red-400 shrink-0"
                              onClick={() => unassignClientKey(k)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
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

      {/* ── TAB 2: Model Registry ────────────────────────────────────────────── */}
      {activeTab === "models" && (
        <div className="grid gap-6 lg:grid-cols-12">
          {/* Traffic Distribution Donut */}
          <Card className="lg:col-span-4 border-border/80 bg-card/60 rounded-2xl shadow-xs">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-bold">Traffic Distribution</CardTitle>
              <CardDescription className="text-xs">Live request split across registered models.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="relative h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={activeModels}
                      dataKey="requests"
                      nameKey="model"
                      cx="50%"
                      cy="50%"
                      innerRadius={65}
                      outerRadius={90}
                      paddingAngle={3}
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
                        borderRadius: "12px",
                        fontSize: "12px",
                      }}
                      formatter={(value) => formatNumber(Number(value))}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <p className="text-2xl font-extrabold text-foreground">{formatNumber(totalRequests)}</p>
                  <p className="text-[11px] text-muted-foreground font-mono">Requests</p>
                </div>
              </div>

              <div className="mt-4 space-y-2">
                {activeModels.map((m) => (
                  <div key={m.model} className="flex items-center justify-between text-xs p-2 rounded-xl bg-muted/20 border border-border/50">
                    <span className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: m.color }} />
                      <span className="font-semibold text-foreground">{m.model}</span>
                    </span>
                    <span className="font-mono text-muted-foreground tabular-nums">{m.percentage}%</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Model Registry Table */}
          <Card className="lg:col-span-8 border-border/80 bg-card/60 rounded-2xl shadow-xs flex flex-col justify-between">
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-3 border-b border-border/60">
              <div>
                <CardTitle className="text-sm font-bold">Registered LLM Providers & Endpoints</CardTitle>
                <CardDescription className="text-xs">Manage API keys, latency baselines, and pricing rates.</CardDescription>
              </div>
              {canEdit && (
                <div className="flex gap-2">
                  <Button
                    size="sm" variant="outline" className="gap-1 text-xs h-8"
                    disabled={rebalancing || totalRequests === 0}
                    onClick={rebalanceFromTraffic}
                  >
                    <RefreshCw className={cn("h-3.5 w-3.5", rebalancing && "animate-spin")} />
                    {rebalancing ? "Rebalancing…" : "Rebalance Shares"}
                  </Button>
                  <Button size="sm" className="gap-1 text-xs h-8" onClick={openCreateModal}>
                    <Plus className="h-3.5 w-3.5" /> Register Provider
                  </Button>
                </div>
              )}
            </CardHeader>

            <CardContent className="pt-4">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border/60 text-muted-foreground font-mono text-[10px] uppercase">
                      <th className="pb-3 text-left">Model / Provider</th>
                      <th className="pb-3 text-left">Latency</th>
                      <th className="pb-3 text-left">Traffic Split</th>
                      <th className="pb-3 text-left">Cost / 1M (In/Out)</th>
                      <th className="pb-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {models.map((m) => (
                      <tr key={m.model} className="hover:bg-muted/20 transition-colors">
                        <td className="py-3 pr-2">
                          <div className="flex items-center gap-2">
                            <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: m.color }} />
                            <div>
                              <p className="font-bold text-foreground text-xs">{m.model}</p>
                              <p className="text-[10px] text-muted-foreground">{providerLabel(m.providerType ?? "custom")}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 font-mono text-muted-foreground">
                          {m.latency} ms
                        </td>
                        <td className="py-3 font-mono">
                          <span className="font-bold text-foreground">{m.percentage}%</span>
                        </td>
                        <td className="py-3 font-mono text-muted-foreground">
                          {formatRatePair(m.costPer1mInput, m.costPer1mOutput)}
                        </td>
                        <td className="py-3 text-right">
                          {canEdit && (
                            <div className="flex items-center justify-end gap-1">
                              <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => openEditModal(m)}>
                                <Pencil className="h-3 w-3" />
                              </Button>
                              <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-400" onClick={() => deleteProvider(m)}>
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── TAB 3: Routing Groups ────────────────────────────────────────────── */}
      {activeTab === "groups" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-foreground">Model Groups & Failover Pools</h2>
              <p className="text-xs text-muted-foreground">Define multi-model clusters with round-robin, lowest-cost, or latency-optimized strategies.</p>
            </div>
            {canEdit && (
              <Button size="sm" className="gap-1 text-xs h-8" onClick={openCreateGroupModal}>
                <Plus className="h-3.5 w-3.5" /> Create Group
              </Button>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {groups.map((group) => (
              <Card key={group.id} className="border-border/80 bg-card/60 rounded-2xl shadow-xs flex flex-col justify-between">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-bold">{group.name}</CardTitle>
                    <Badge variant="outline" className="text-[10px] font-mono uppercase bg-primary/5 text-primary border-primary/20">
                      {group.strategy}
                    </Badge>
                  </div>
                  <CardDescription className="text-xs">{group.description || "No description provided."}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 pt-2">
                  <div className="space-y-1">
                    <p className="text-[10px] font-mono uppercase text-muted-foreground">Cluster Members</p>
                    <div className="flex flex-wrap gap-1.5">
                      {group.members.map((mem) => (
                        <span key={mem.model} className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-muted/40 border border-border/60 font-mono">
                          {mem.model} ({mem.weight}%)
                        </span>
                      ))}
                    </div>
                  </div>
                  {canEdit && (
                    <div className="pt-2 border-t border-border/50 flex items-center justify-end gap-1.5">
                      <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => openEditGroupModal(group)}>
                        <Pencil className="h-3 w-3" /> Edit
                      </Button>
                      <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-400" onClick={() => deleteGroup(group)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* ── TAB 4: Gateway & Aliases ─────────────────────────────────────────── */}
      {activeTab === "gateway" && <UagAdminPanel />}

      {/* ── TAB 5: Performance & SLA ─────────────────────────────────────────── */}
      {activeTab === "performance" && (
        <Card className="border-border/80 bg-card/60 rounded-2xl shadow-xs">
          <CardHeader>
            <CardTitle className="text-sm font-bold">Latency Timeline & SLA Breakdown</CardTitle>
            <CardDescription className="text-xs">Hourly latency variations across registered provider clusters.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={perfData}>
                  <XAxis dataKey="hour" stroke="#888888" fontSize={11} />
                  <YAxis stroke="#888888" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "12px",
                      fontSize: "12px",
                    }}
                  />
                  {activeModels.map((m) => (
                    <Area
                      key={m.model}
                      type="monotone"
                      dataKey={m.model}
                      stroke={m.color}
                      fill={m.color}
                      fillOpacity={0.15}
                      strokeWidth={2}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── TAB 6: Cost Arbitrage ROI ────────────────────────────────────────── */}
      {activeTab === "cost" && (
        <div className="grid gap-6 lg:grid-cols-12">
          <Card className="lg:col-span-4 border-border/80 bg-card/60 rounded-2xl shadow-xs flex flex-col justify-between">
            <CardHeader>
              <CardTitle className="text-sm font-bold">Cost Arbitrage Summary</CardTitle>
              <CardDescription className="text-xs">Financial optimization metrics.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
                <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">Total Savings</p>
                <p className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">{formatUsd(savedEstimate)}</p>
                <p className="text-[11px] text-muted-foreground mt-1">Versus unrouted premium model rates</p>
              </div>

              <div className="rounded-xl border border-border/60 bg-muted/20 p-4">
                <p className="text-xs font-semibold text-muted-foreground">30-Day Total Spend</p>
                <p className="text-2xl font-bold text-foreground mt-1">{formatUsd(totalSpend)}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-8 border-border/80 bg-card/60 rounded-2xl shadow-xs">
            <CardHeader>
              <CardTitle className="text-sm font-bold">Daily Spend Trend (USD)</CardTitle>
              <CardDescription className="text-xs">Token consumption and cost timeline.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={costTrend}>
                    <XAxis dataKey="date" stroke="#888888" fontSize={11} />
                    <YAxis stroke="#888888" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "12px",
                        fontSize: "12px",
                      }}
                      formatter={(v) => formatUsd(Number(v))}
                    />
                    <Area type="monotone" dataKey="cost_usd" stroke="#10b981" fill="#10b981" fillOpacity={0.2} strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Modals */}
      <LlmProviderModal
        open={modalOpen}
        provider={editingProvider}
        token={token}
        onClose={() => setModalOpen(false)}
        onSaved={() => {
          invalidateProviders();
          setModalOpen(false);
        }}
      />
      <RoutingRuleModal
        open={ruleModalOpen}
        rule={editingRule}
        targetModels={targetModelOptions}
        token={token}
        onClose={() => setRuleModalOpen(false)}
        onSaved={() => {
          invalidateRules();
          setRuleModalOpen(false);
        }}
      />
      <RoutingGroupModal
        open={groupModalOpen}
        group={editingGroup}
        token={token}
        onClose={() => setGroupModalOpen(false)}
        onSaved={() => {
          fetchGroups();
          setGroupModalOpen(false);
        }}
      />
      {selectedRule && (
        <AssignClientKeyModal
          open={assignKeyModalOpen}
          rule={{ id: selectedRule.id, name: selectedRule.name }}
          clientApiKeys={clientApiKeys}
          assignedKeyIds={assignedKeyIds}
          token={token}
          onClose={() => setAssignKeyModalOpen(false)}
          onAssigned={() => fetchAssignedKeys(selectedRule.id)}
        />
      )}
    </div>
  );
}
