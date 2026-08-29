"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { RoutingModel } from "@/lib/mock-data";
import type { McpServer } from "@/lib/types/domain";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { governanceNodes, governanceEdges } from "@/lib/governance-topology";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { GovernanceNode, type GovernanceNodeData } from "@/components/governance/governance-node";
import { QuickLinkPills, SectionTabBar } from "@/components/shared/section-chrome";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useMcpServers } from "@/hooks/use-mcp-servers";
import { useLlmRouting } from "@/hooks/use-llm-routing";
import { ArrowRight, GitBranch, Route, Server, Shield, Workflow } from "lucide-react";
import { usePolicyGraphLinks } from "@/hooks/use-policy-graph-links";
import { policyStudioUrl } from "@/lib/policy-graph-map";
import { Button } from "@/components/ui/button";

const QUICK_LINKS = [
  { href: "/policy-studio", label: "Policy Studio", icon: Workflow },
  { href: "/ai-gateway", label: "AI Gateway", icon: Shield },
  { href: "/llm-router", label: "LLM Router", icon: Route },
  { href: "/mcp-governance", label: "MCP Governance", icon: Server },
] as const;

const EMPTY_NODE_IDS: string[] = [];
const EMPTY_MCP_SERVERS: McpServer[] = [];

const nodeTypes = { governance: GovernanceNode };
const modelColors = ["#3b82f6", "#8b5cf6", "#f97316", "#22c55e", "#6366f1"];
const edgeStyle = { stroke: "#94a3b8", strokeWidth: 2 };
const modelEdgeStyle = { stroke: "#6366f1", strokeWidth: 2, strokeDasharray: "6 4" };

type SideTab = "inspect" | "flows";

function buildFlowGraph(
  mcpStatus: string | undefined,
  gatewayMode: string | undefined,
  models: Pick<RoutingModel, "model" | "successRate">[],
  highlightNodeId: string | null,
  bundleHighlightIds: string[] = []
): { nodes: Node<GovernanceNodeData>[]; edges: Edge[] } {
  const highlightSet = new Set(bundleHighlightIds);
  const modelNodes = models.slice(0, 4).map((m, i) => ({
    id: `model-${i}`,
    label: m.model,
    type: "model" as const,
    x: 80 + i * 170,
    y: 440,
    color: modelColors[i % modelColors.length],
    status: m.successRate >= 98 ? "healthy" : m.successRate >= 95 ? "degraded" : "offline",
  }));

  const coreNodes = governanceNodes
    .filter((n) => n.type !== "model")
    .map((n) => {
      let status: string | undefined;
      if (n.id === "gateway") status = gatewayMode === "ollama" ? "ollama" : gatewayMode ?? "operational";
      if (n.id === "mcp") status = mcpStatus ?? "healthy";
      if (n.type === "policy" || n.type === "dlp") status = "active";
      if (n.type === "audit") status = "recording";
      return { ...n, status };
    });

  const allNodes = [...coreNodes, ...(modelNodes.length ? modelNodes : governanceNodes.filter((n) => n.type === "model"))];

  const nodes: Node<GovernanceNodeData>[] = allNodes.map((n) => ({
    id: n.id,
    type: "governance",
    position: { x: n.x - 60, y: n.y - 20 },
    selected: highlightNodeId === n.id,
    data: {
      label: n.label,
      nodeType: n.type,
      color: n.color,
      status: n.status,
      highlighted: highlightNodeId === n.id || highlightSet.has(n.id),
    },
  }));

  const modelIds = allNodes.filter((n) => n.type === "model").map((n) => n.id);
  const nodeIds = new Set(allNodes.map((n) => n.id));

  const coreEdges: Edge[] = governanceEdges
    .filter((e) => nodeIds.has(e.from) && nodeIds.has(e.to))
    .map((e) => ({
      id: `${e.from}-${e.to}`,
      source: e.from,
      target: e.to,
      type: "smoothstep",
      label: e.label,
      animated: false,
      markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8", width: 16, height: 16 },
      style: edgeStyle,
      labelStyle: { fill: "#64748b", fontSize: 11, fontWeight: 600 },
      labelBgStyle: { fill: "#ffffff", fillOpacity: 0.95 },
      labelBgPadding: [6, 4] as [number, number],
      labelBgBorderRadius: 4,
      data: { correlation: e.correlation },
    }));

  const modelEdges: Edge[] = modelIds.map((id) => ({
    id: `mcp-${id}`,
    source: "mcp",
    target: id,
    type: "smoothstep",
    label: "route",
    animated: false,
    markerEnd: { type: MarkerType.ArrowClosed, color: "#6366f1", width: 16, height: 16 },
    style: modelEdgeStyle,
    labelStyle: { fill: "#64748b", fontSize: 11 },
    labelBgStyle: { fill: "#ffffff", fillOpacity: 0.95 },
    data: { correlation: "LLM Router forwards approved requests to upstream models" },
  }));

  return { nodes, edges: [...coreEdges, ...modelEdges] };
}

function nodeLabel(id: string, nodes: Node<GovernanceNodeData>[]) {
  return nodes.find((n) => n.id === id)?.data.label ?? id;
}

export function GovernanceGraphView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nodeFromUrl = searchParams.get("node");
  const policyFromUrl = searchParams.get("policy");
  const token = useAuthStore((s) => s.token);
  const { data: mcpServersData, isLoading: mcpLoading } = useMcpServers();
  const mcpServers = mcpServersData ?? EMPTY_MCP_SERVERS;
  const { models, isLoading: routingLoading } = useLlmRouting();
  const [manualNodeId, setManualNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [selectedBindingId, setSelectedBindingId] = useState<string>("__jwt_default__");
  const [sideTab, setSideTab] = useState<SideTab>("inspect");
  const selectedNodeId = manualNodeId ?? nodeFromUrl;
  const activeNodeId = selectedNodeId ?? nodeFromUrl;
  const { data: linkedPolicies = [] } = usePolicyGraphLinks(activeNodeId ?? undefined);

  const { data: ingressBindings = [], isLoading: bindingsLoading } = useQuery({
    queryKey: ["ingress-bindings", token],
    queryFn: () => api.getIngressBindings(token!),
    enabled: !!token,
  });

  const graphLoading = Boolean(token) && (mcpLoading || routingLoading || bindingsLoading);

  const selectedBinding =
    ingressBindings.find((b) => b.id === selectedBindingId) ?? ingressBindings[0] ?? null;

  useEffect(() => {
    if (ingressBindings.length > 0 && !ingressBindings.some((b) => b.id === selectedBindingId)) {
      setSelectedBindingId(ingressBindings[0].id);
    }
  }, [ingressBindings, selectedBindingId]);

  const bundleHighlightIds = selectedBinding?.graph_node_ids ?? EMPTY_NODE_IDS;

  const bindingPolicies =
    selectedBinding && activeNodeId
      ? selectedBinding.policies.filter((p) => p.graph_node_id === activeNodeId)
      : selectedBinding?.policies ?? [];

  const { data: gatewayStatus } = useQuery({
    queryKey: ["gateway-status-graph", token],
    queryFn: async () => {
      if (!token) return null;
      try {
        return await api.getGatewayStatus(token);
      } catch {
        return null;
      }
    },
    enabled: !!token,
  });

  const mcpAggregate = mcpServers.some((s) => s.status === "offline")
    ? "degraded"
    : mcpServers.some((s) => s.status === "degraded")
      ? "degraded"
      : "healthy";

  const { nodes, edges } = useMemo(
    () => buildFlowGraph(mcpAggregate, gatewayStatus?.proxy_mode, models, activeNodeId, bundleHighlightIds),
    [mcpAggregate, gatewayStatus?.proxy_mode, models, activeNodeId, bundleHighlightIds]
  );

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null;
  const selectedEdge = edges.find((e) => e.id === selectedEdgeId) ?? null;
  const hasSelection = Boolean(selectedNode || selectedEdge);

  const allCorrelations = useMemo(
    () =>
      governanceEdges.map((e) => ({
        from: governanceNodes.find((n) => n.id === e.from)?.label ?? e.from,
        to: governanceNodes.find((n) => n.id === e.to)?.label ?? e.to,
        label: e.label,
        detail: e.correlation,
      })),
    []
  );

  const correlations = useMemo(() => {
    if (selectedEdge) {
      return [
        {
          from: nodeLabel(selectedEdge.source, nodes),
          to: nodeLabel(selectedEdge.target, nodes),
          label: String(selectedEdge.label ?? "connects"),
          detail: (selectedEdge.data as { correlation?: string })?.correlation ?? "",
        },
      ];
    }
    if (!selectedNode) return allCorrelations;

    return edges
      .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
      .map((e) => ({
        from: nodeLabel(e.source, nodes),
        to: nodeLabel(e.target, nodes),
        label: String(e.label ?? "connects"),
        detail: (e.data as { correlation?: string })?.correlation ?? "",
      }));
  }, [selectedNode, selectedEdge, edges, nodes, allCorrelations]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setManualNodeId(node.id);
    setSelectedEdgeId(null);
    setSideTab("inspect");
    router.replace(`/governance-graph?node=${encodeURIComponent(node.id)}`, { scroll: false });
  }, [router]);

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedEdgeId(edge.id);
    setManualNodeId(null);
    setSideTab("inspect");
  }, []);

  const clearSelection = useCallback(() => {
    setManualNodeId(null);
    setSelectedEdgeId(null);
    router.replace("/governance-graph", { scroll: false });
  }, [router]);

  return (
    <div className="space-y-6">
      <QuickLinkPills links={QUICK_LINKS} />

      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-violet-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2.5 max-w-xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Live Ingress Topology
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <GitBranch className="h-3.5 w-3.5 text-primary" />
                Interactive ReactFlow Mesh
              </Badge>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              Governance Topology & Visual Mesh
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Interactive visual topology mapping data paths from client ingress keys through OPA policy evaluation, Presidio PII redaction, LLM routing, and upstream provider pools.
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-3 shrink-0">
            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Topology Nodes</span>
                <Workflow className="h-3.5 w-3.5 text-primary" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-foreground">{nodes.length}</p>
              <p className="text-[10px] text-muted-foreground">Mesh elements</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Connections</span>
                <GitBranch className="h-3.5 w-3.5 text-violet-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-foreground">{edges.length}</p>
              <p className="text-[10px] text-muted-foreground">Data pipelines</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-12">
        <Card className="overflow-hidden border-border/80 bg-card/60 rounded-2xl shadow-xs xl:col-span-9">
          <CardHeader className="space-y-3 pb-3 border-b border-border/60">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-sm font-bold">
                <GitBranch className="h-4 w-4 text-primary" />
                Live Flow Graph
              </CardTitle>
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground font-mono">
                <span>{nodes.length} nodes</span>
                <span>·</span>
                <span>{edges.length} connections</span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {ingressBindings.length > 0 && (
                <select
                  value={selectedBinding?.id ?? ""}
                  onChange={(e) => setSelectedBindingId(e.target.value)}
                  className="h-8 max-w-[240px] rounded-md border border-input bg-background px-2 text-xs"
                  aria-label="Ingress binding"
                >
                  {ingressBindings.map((binding) => (
                    <option key={binding.id} value={binding.id}>
                      {binding.name}
                    </option>
                  ))}
                </select>
              )}
              <Badge variant="outline" className="gap-1.5 font-normal">
                <span className="inline-block h-0.5 w-3 bg-slate-400" />
                Governance
              </Badge>
              <Badge variant="outline" className="gap-1.5 font-normal">
                <span className="inline-block h-0.5 w-3 border-t-2 border-dashed border-indigo-400" />
                Model route
              </Badge>
              {hasSelection && (
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={clearSelection}>
                  Clear selection
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-[min(68vh,640px)] w-full pysetu-flow">
              {graphLoading ? (
                <div className="flex h-full items-center justify-center bg-muted/10">
                  <p className="text-sm text-muted-foreground">Loading governance graph…</p>
                </div>
              ) : (
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodeClick={onNodeClick}
                  onEdgeClick={onEdgeClick}
                  onPaneClick={clearSelection}
                  nodeTypes={nodeTypes}
                  nodesDraggable={false}
                  nodesConnectable={false}
                  elementsSelectable={false}
                  fitView
                  fitViewOptions={{ padding: 0.18 }}
                  minZoom={0.35}
                  maxZoom={1.5}
                  defaultEdgeOptions={{ type: "smoothstep", style: edgeStyle }}
                  proOptions={{ hideAttribution: true }}
                >
                  <Background gap={16} size={1} color="#e2e8f0" />
                  <Controls showInteractive={false} />
                </ReactFlow>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/50 xl:col-span-3">
          <CardHeader className="space-y-3 pb-2">
            <CardTitle className="text-sm">
              {selectedEdge ? "Connection" : selectedNode ? selectedNode.data.label : "Graph explorer"}
            </CardTitle>
            <SectionTabBar
              tabs={[
                { id: "inspect", label: "Inspect" },
                { id: "flows", label: "All flows" },
              ]}
              active={sideTab}
              onChange={setSideTab}
            />
          </CardHeader>
          <CardContent className="max-h-[min(68vh,640px)] space-y-3 overflow-y-auto">
            {sideTab === "inspect" && (
              <>
                {!hasSelection && (
                  <div className="space-y-3 rounded-md border border-border/60 bg-muted/10 p-3 text-xs text-muted-foreground">
                    <p>Click a node or connection on the graph to inspect policies, ingress bindings, and related flows.</p>
                    {selectedBinding && (
                      <div className="space-y-1 border-t border-border/60 pt-2 text-foreground">
                        <p>
                          Binding: <span className="font-medium">{selectedBinding.name}</span>
                        </p>
                        <p>
                          Bundle: <span className="font-medium">{selectedBinding.bundle_name ?? "—"}</span>
                        </p>
                        <p>{selectedBinding.policies.length} policies · {selectedBinding.graph_node_ids.length} stages</p>
                      </div>
                    )}
                    {mcpServers.length > 0 && (
                      <p className="border-t border-border/60 pt-2">
                        MCP aggregate: <span className="capitalize text-foreground">{mcpAggregate}</span> across{" "}
                        {mcpServers.length} servers —{" "}
                        <Link href="/mcp-governance" className="text-primary hover:underline">
                          manage servers
                        </Link>
                      </p>
                    )}
                  </div>
                )}

                {selectedNode && (
                  <>
                    <div className="flex items-center gap-2">
                      <div className="h-4 w-4 rounded-full" style={{ backgroundColor: selectedNode.data.color }} />
                      <span className="font-medium">{selectedNode.data.label}</span>
                    </div>
                    <Badge variant="outline" className="capitalize">
                      {selectedNode.data.nodeType}
                    </Badge>
                    {selectedNode.data.status && (
                      <p className="text-sm text-muted-foreground">
                        Status: <span className="capitalize text-foreground">{selectedNode.data.status}</span>
                      </p>
                    )}
                    {["policy", "dlp", "mcp", "gateway"].includes(selectedNode.id) &&
                      (bindingPolicies.length > 0 ? bindingPolicies : linkedPolicies).length > 0 && (
                        <div className="space-y-2 border-t border-border pt-3">
                          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            {selectedBinding
                              ? `Policies — ${selectedBinding.bundle_name ?? selectedBinding.name}`
                              : "Linked policies"}
                          </p>
                          {(bindingPolicies.length > 0 ? bindingPolicies : linkedPolicies).map((link) => (
                            <div
                              key={link.policy_id}
                              className={`rounded-md border p-2 text-xs ${
                                policyFromUrl === link.policy_id ? "border-primary bg-primary/5" : "border-border/60"
                              }`}
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-medium">{link.policy_name}</span>
                                {"policy_status" in link && link.policy_status && (
                                  <Badge variant="outline" className="text-[10px] capitalize">
                                    {link.policy_status}
                                  </Badge>
                                )}
                              </div>
                              <Button variant="link" size="sm" className="h-auto p-0 text-xs" asChild>
                                <Link href={policyStudioUrl(link.policy_id)}>
                                  <Workflow className="mr-1 inline h-3 w-3" />
                                  Policy Studio
                                </Link>
                              </Button>
                            </div>
                          ))}
                        </div>
                      )}
                    {selectedNode.id === "gateway" && selectedBinding && (
                      <div className="space-y-1 border-t border-border pt-3 text-xs text-muted-foreground">
                        <p>
                          Ingress: <span className="text-foreground">{selectedBinding.name}</span>
                        </p>
                        <p>
                          Bundle: <span className="text-foreground">{selectedBinding.bundle_name ?? "—"}</span>
                        </p>
                      </div>
                    )}
                    {selectedNode.id === "gateway" && gatewayStatus && (
                      <div className="space-y-1 border-t border-border pt-3 text-sm">
                        <p>Requests today: {gatewayStatus.requests_today.toLocaleString()}</p>
                        <p>Blocked today: {gatewayStatus.blocked_today.toLocaleString()}</p>
                      </div>
                    )}
                    {selectedNode.id === "mcp" && (
                      <Button variant="outline" size="sm" className="w-full gap-1.5" asChild>
                        <Link href="/mcp-governance">
                          <Server className="h-3.5 w-3.5" />
                          Open MCP Governance
                        </Link>
                      </Button>
                    )}
                  </>
                )}

                {hasSelection && correlations.length > 0 && (
                  <div className="space-y-2 border-t border-border pt-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Related flows</p>
                    {correlations.map((c) => (
                      <CorrelationRow key={`${c.from}-${c.to}-${c.label}`} {...c} />
                    ))}
                  </div>
                )}
              </>
            )}

            {sideTab === "flows" && (
              <div className="space-y-2">
                {allCorrelations.map((c) => (
                  <CorrelationRow key={`${c.from}-${c.to}-${c.label}`} {...c} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function CorrelationRow({
  from,
  to,
  label,
  detail,
}: {
  from: string;
  to: string;
  label: string;
  detail: string;
}) {
  return (
    <div className="rounded-md border border-border/60 bg-muted/10 p-2 text-xs">
      <div className="flex items-center gap-1 font-medium">
        <span>{from}</span>
        <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />
        <span>{to}</span>
        <Badge variant="outline" className="ml-auto shrink-0 text-[10px]">
          {label}
        </Badge>
      </div>
      <p className="mt-1 text-muted-foreground">{detail}</p>
    </div>
  );
}
