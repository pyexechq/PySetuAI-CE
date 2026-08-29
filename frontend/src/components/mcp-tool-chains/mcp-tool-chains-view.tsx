"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTheme } from "next-themes";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  GitBranch,
  Loader2,
  Plus,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  SlidersHorizontal,
  Trash2,
  Workflow,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiMcpToolChainEvent, type ApiMcpToolChainSummary, type ApiMcpToolPolicy } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

function riskVariant(score: number): "default" | "secondary" | "warning" | "destructive" | "success" | "outline" {
  if (score >= 80) return "destructive";
  if (score >= 60) return "warning";
  if (score >= 30) return "secondary";
  return "success";
}

function riskLabel(score: number): string {
  if (score >= 80) return "Critical";
  if (score >= 60) return "High";
  if (score >= 30) return "Medium";
  return "Low";
}

function decisionVariant(decision: string): "default" | "secondary" | "warning" | "destructive" | "success" | "outline" {
  if (decision === "allowed") return "success";
  if (decision === "blocked") return "destructive";
  if (decision === "approval") return "warning";
  return "secondary";
}

function McpToolChainsViewInner() {
  const token = useAuthStore((s) => s.token);
  const { resolvedTheme } = useTheme();
  
  const [activeTab, setActiveTab] = useState<"overview" | "events" | "policies">("overview");
  const [decisionFilter, setDecisionFilter] = useState<string>("all");

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["mcp-tool-chain-summary", token],
    queryFn: () => api.getMcpToolChainSummary(token!),
    enabled: Boolean(token),
  });

  const { data: events = [], isLoading: eventsLoading } = useQuery({
    queryKey: ["mcp-tool-chains", token, decisionFilter],
    queryFn: () => api.getMcpToolChains(token!, 200, decisionFilter),
    enabled: Boolean(token) && activeTab === "events",
  });

  const { data: graph, isLoading: graphLoading } = useQuery({
    queryKey: ["mcp-tool-chain-graph", token],
    queryFn: () => api.getMcpToolChainGraph(token!, 200),
    enabled: Boolean(token) && activeTab === "overview",
  });

  const { data: toolPolicies = [], isLoading: toolPoliciesLoading } = useQuery({
    queryKey: ["mcp-tool-policies", token],
    queryFn: () => api.getMcpToolPolicies(token!),
    enabled: Boolean(token) && activeTab === "policies",
  });

  const { data: mcpServers = [] } = useQuery({
    queryKey: ["mcp-servers", token],
    queryFn: () => api.getMcpServers(token!),
    enabled: Boolean(token) && activeTab === "policies",
  });

  const queryClient = useQueryClient();
  const [newPolicyServer, setNewPolicyServer] = useState("");
  const [newPolicyTool, setNewPolicyTool] = useState("");
  const [newPolicyAction, setNewPolicyAction] = useState<"allow" | "approval" | "block">("block");
  const [newPolicyReason, setNewPolicyReason] = useState("");

  const upsertPolicy = useMutation({
    mutationFn: () =>
      api.upsertMcpToolPolicy(token!, {
        server_id: newPolicyServer,
        tool_name: newPolicyTool,
        action: newPolicyAction,
        reason: newPolicyReason || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-tool-policies"] });
      setNewPolicyServer("");
      setNewPolicyTool("");
      setNewPolicyAction("block");
      setNewPolicyReason("");
    },
  });

  const deletePolicy = useMutation({
    mutationFn: (policyId: string) => api.deleteMcpToolPolicy(token!, policyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["mcp-tool-policies"] }),
  });

  const flowNodes: Node[] = useMemo(() => {
    if (!graph) return [];
    const isDark = resolvedTheme === "dark";
    return graph.nodes.map((node, index) => ({
      id: node.id,
      position: { x: (index % 5) * 220, y: Math.floor(index / 5) * 160 },
      data: { label: node.label },
      style: {
        border: `1px solid ${node.color}`,
        borderRadius: 8,
        padding: "6px 10px",
        background: `${node.color}${isDark ? "33" : "1a"}`,
        color: isDark ? "#f8fafc" : "#0f172a",
        fontSize: 12,
      },
    }));
  }, [graph, resolvedTheme]);

  const flowEdges: Edge[] = useMemo(() => {
    if (!graph) return [];
    const isDark = resolvedTheme === "dark";
    return graph.edges.map((edge, index) => ({
      id: `e-${index}`,
      source: edge.from,
      target: edge.to,
      label: edge.label,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: edge.risk_score >= 60 ? "#ef4444" : "#94a3b8", strokeWidth: 1.5 },
      labelStyle: { fontSize: 10, fill: isDark ? "#e2e8f0" : "#475569", fontWeight: 600 },
      labelBgStyle: { fill: isDark ? "#0f172a" : "#ffffff", fillOpacity: 0.92 },
      labelBgPadding: [4, 2],
    }));
  }, [graph, resolvedTheme]);

  const s: ApiMcpToolChainSummary = summary ?? {
    total: 0,
    allowed: 0,
    blocked: 0,
    approval: 0,
    high_risk: 0,
    by_decision: {},
    by_tool_risk: {},
    by_external_service: {},
  };

  return (
    <div className="space-y-6">
      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2.5 max-w-xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Chain Execution Guardrail Active
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <Workflow className="h-3.5 w-3.5 text-primary" />
                Multi-Hop Graph Sandbox
              </Badge>
              <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-xs font-mono">
                Cascade Loop Breaker
              </Badge>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              MCP Tool Chains & Execution Graph
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Visualize and govern multi-hop agent tool sequences, detect privilege escalation cycles, enforce step-by-step human sign-offs, and monitor cross-service hops.
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-3 shrink-0">
            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Total Events</span>
                <Workflow className="h-3.5 w-3.5 text-primary" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-foreground">{summaryLoading ? "…" : s.total}</p>
              <p className="text-[10px] text-muted-foreground">Governed tool hops</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Allowed</span>
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-emerald-600 dark:text-emerald-400">{summaryLoading ? "…" : s.allowed}</p>
              <p className="text-[10px] text-muted-foreground">Policy approved</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Blocked</span>
                <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-rose-600 dark:text-rose-400">{summaryLoading ? "…" : s.blocked}</p>
              <p className="text-[10px] text-muted-foreground">Interceptions</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">High Risk</span>
                <GitBranch className="h-3.5 w-3.5 text-amber-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-amber-600 dark:text-amber-400">{summaryLoading ? "…" : s.high_risk}</p>
              <p className="text-[10px] text-muted-foreground">Sensitive chains</p>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Navigation Tabs ──────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs">
          {[
            { id: "overview", label: "Execution Graph & Topology" },
            { id: "events", label: "Tool Chain Audit Events" },
            { id: "policies", label: "Step-Level Tool Policies" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as any)}
              className={cn(
                "px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all",
                activeTab === tab.id
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "overview" && (
        <div className="space-y-6 animate-in fade-in zoom-in-95 duration-200">
          <Card className="border-border/80 bg-card/60 rounded-2xl shadow-xs">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="h-5 w-5" />
                Agentic Attack Surface Map
              </CardTitle>
              <CardDescription>
                Agent → agent → MCP server → tool → data → external service chains. Red edges are high-risk.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {graphLoading ? (
                <div className="flex h-[420px] items-center justify-center rounded-xl border border-dashed border-border/60">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground/50" />
                </div>
              ) : graph && graph.nodes.length > 0 ? (
                <div className="h-[420px] overflow-hidden rounded-xl border border-border/60">
                  <ReactFlow
                    nodes={flowNodes}
                    edges={flowEdges}
                    fitView
                    nodesDraggable
                    nodesConnectable={false}
                    elementsSelectable
                    proOptions={{ hideAttribution: true }}
                  >
                    <Background gap={16} size={1} />
                    <Controls />
                  </ReactFlow>
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
                  <GitBranch className="mx-auto h-8 w-8 text-muted-foreground/50" />
                  <p className="mt-3 font-medium">No tool chains recorded yet</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Invoke an MCP tool through the gateway to begin building the attack surface map.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === "events" && (
        <div className="animate-in fade-in zoom-in-95 duration-200">
          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Workflow className="h-5 w-5" />
                Tool Chain Events
              </CardTitle>
              <CardDescription>Recent MCP tool invocations and their governance decisions.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4 flex flex-wrap gap-2">
                {["all", "allowed", "blocked", "approval"].map((decision) => (
                  <Button
                    key={decision}
                    variant={decisionFilter === decision ? "default" : "outline"}
                    size="sm"
                    onClick={() => setDecisionFilter(decision)}
                  >
                    {decision === "all" ? "All" : decision[0].toUpperCase() + decision.slice(1)}
                  </Button>
                ))}
              </div>
              
              {eventsLoading ? (
                <div className="flex h-[200px] items-center justify-center rounded-xl border border-dashed border-border/60">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground/50" />
                </div>
              ) : events.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
                  <Workflow className="mx-auto h-8 w-8 text-muted-foreground/50" />
                  <p className="mt-3 font-medium">No chain events</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    MCP tool invocations will appear here as they are governed.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {events.map((event: ApiMcpToolChainEvent) => (
                    <div
                      key={event.id}
                      className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
                    >
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-medium">{event.mcp_server_name}</p>
                          <Badge variant="outline">{event.tool_name}</Badge>
                          <Badge variant={decisionVariant(event.decision)}>{event.decision}</Badge>
                          <Badge variant="outline">{event.tool_risk}</Badge>
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {event.external_service ? `→ ${event.external_service}` : ""}
                          {event.data_source ? ` · ${event.data_source}` : ""}
                          {event.policy_name ? ` · policy: ${event.policy_name}` : ""}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {new Date(event.created_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <Badge variant={riskVariant(event.chain_risk_score)}>
                          {riskLabel(event.chain_risk_score)} · {event.chain_risk_score}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === "policies" && (
        <div className="animate-in fade-in zoom-in-95 duration-200">
          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SlidersHorizontal className="h-5 w-5" />
                Per-Tool Policies
              </CardTitle>
              <CardDescription>
                Override the default decision for a specific MCP tool. These take precedence over the bundle MCP scope.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {toolPoliciesLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading per-tool policies...
                </div>
              ) : toolPolicies.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border/60 p-6 text-center">
                  <SlidersHorizontal className="mx-auto h-7 w-7 text-muted-foreground/50" />
                  <p className="mt-2 font-medium">No per-tool policies</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Add a policy to allow, require approval for, or block a specific MCP tool.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {toolPolicies.map((policy: ApiMcpToolPolicy) => {
                    const server = mcpServers.find((s) => s.id === policy.server_id);
                    return (
                      <div
                        key={policy.id}
                        className="flex flex-col gap-2 rounded-lg border border-border/60 bg-background/50 p-3 md:flex-row md:items-center md:justify-between"
                      >
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-medium">{server?.name ?? policy.server_id}</p>
                            <Badge variant="outline">{policy.tool_name}</Badge>
                            <Badge variant={decisionVariant(policy.action)}>{policy.action}</Badge>
                            {policy.risk_score > 0 && (
                              <Badge variant={riskVariant(policy.risk_score)}>risk {policy.risk_score}</Badge>
                            )}
                          </div>
                          {policy.reason && (
                            <p className="mt-1 text-sm text-muted-foreground">{policy.reason}</p>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive"
                          onClick={() => deletePolicy.mutate(policy.id)}
                          disabled={deletePolicy.isPending}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}

              <div className="space-y-2 rounded-lg border border-dashed border-border/60 p-3">
                <p className="text-sm font-medium">Add per-tool policy</p>
                <div className="grid gap-2 md:grid-cols-2">
                  <select
                    value={newPolicyServer}
                    onChange={(e) => {
                      setNewPolicyServer(e.target.value);
                      const selected = mcpServers.find((s) => s.id === e.target.value);
                      setNewPolicyTool(selected?.tool_names?.[0] ?? "");
                    }}
                    className="flex h-9 rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="">Select MCP server</option>
                    {mcpServers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                  <select
                    value={newPolicyTool}
                    onChange={(e) => setNewPolicyTool(e.target.value)}
                    className="flex h-9 rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="">Select tool</option>
                    {mcpServers
                      .find((s) => s.id === newPolicyServer)
                      ?.tool_names.map((tool) => (
                        <option key={tool} value={tool}>{tool}</option>
                      ))}
                  </select>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {(["allow", "approval", "block"] as const).map((action) => (
                    <label key={action} className="flex items-center gap-1.5 text-sm">
                      <input
                        type="radio"
                        name="policy-action"
                        checked={newPolicyAction === action}
                        onChange={() => setNewPolicyAction(action)}
                      />
                      {action}
                    </label>
                  ))}
                </div>
                <input
                  value={newPolicyReason}
                  onChange={(e) => setNewPolicyReason(e.target.value)}
                  placeholder="Reason (optional)"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                />
                <Button
                  size="sm"
                  className="gap-2"
                  disabled={!newPolicyServer || !newPolicyTool || upsertPolicy.isPending}
                  onClick={() => upsertPolicy.mutate()}
                >
                  {upsertPolicy.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  Save policy
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export function McpToolChainsView() {
  return <McpToolChainsViewInner />;
}
