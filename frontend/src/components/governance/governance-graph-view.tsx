"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { RoutingModel } from "@/lib/mock-data";
import type { McpServer } from "@/lib/types/domain";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
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
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useMcpServers } from "@/hooks/use-mcp-servers";
import { useLlmRouting } from "@/hooks/use-llm-routing";
import { ArrowRight, Workflow } from "lucide-react";
import { usePolicyGraphLinks } from "@/hooks/use-policy-graph-links";
import { policyStudioUrl } from "@/lib/policy-graph-map";
import { Button } from "@/components/ui/button";

const EMPTY_NODE_IDS: string[] = [];
const EMPTY_MCP_SERVERS: McpServer[] = [];

const nodeTypes = { governance: GovernanceNode };
const modelColors = ["#3b82f6", "#8b5cf6", "#f97316", "#22c55e", "#6366f1"];
const edgeStyle = { stroke: "#94a3b8", strokeWidth: 2 };
const modelEdgeStyle = { stroke: "#6366f1", strokeWidth: 2, strokeDasharray: "6 4" };

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
    if (!selectedNode) return governanceEdges.map((e) => ({
      from: governanceNodes.find((n) => n.id === e.from)?.label ?? e.from,
      to: governanceNodes.find((n) => n.id === e.to)?.label ?? e.to,
      label: e.label,
      detail: e.correlation,
    }));

    return edges
      .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
      .map((e) => ({
        from: nodeLabel(e.source, nodes),
        to: nodeLabel(e.target, nodes),
        label: String(e.label ?? "connects"),
        detail: (e.data as { correlation?: string })?.correlation ?? "",
      }));
  }, [selectedNode, selectedEdge, edges, nodes]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setManualNodeId(node.id);
    setSelectedEdgeId(null);
  }, []);

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedEdgeId(edge.id);
    setManualNodeId(null);
  }, []);

  return (
    <div className="grid gap-4 lg:grid-cols-4">
      <Card className="lg:col-span-3 border-border/60 bg-card/50 overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>Governance Topology</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            {ingressBindings.length > 0 && (
              <select
                value={selectedBinding?.id ?? ""}
                onChange={(e) => setSelectedBindingId(e.target.value)}
                className="h-8 max-w-[220px] rounded-md border border-input bg-background px-2 text-xs"
                aria-label="Ingress binding"
              >
                {ingressBindings.map((binding) => (
                  <option key={binding.id} value={binding.id}>
                    {binding.name}
                  </option>
                ))}
              </select>
            )}
            <Badge variant="outline">{nodes.length} nodes</Badge>
            <Badge variant="secondary">{edges.length} connections</Badge>
            <Badge variant="outline" className="gap-1 font-normal">
              <span className="inline-block h-0.5 w-4 bg-slate-400" /> Governance flow
            </Badge>
            <Badge variant="outline" className="gap-1 font-normal">
              <span className="inline-block h-0.5 w-4 border-t-2 border-dashed border-indigo-400" /> Model route
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="h-[520px] w-full pysetu-flow">
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
              onPaneClick={() => {
                setManualNodeId(null);
                setSelectedEdgeId(null);
              }}
              nodeTypes={nodeTypes}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
              fitView
              fitViewOptions={{ padding: 0.2 }}
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

      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="text-sm">
            {selectedEdge ? "Connection" : selectedNode ? "Node Details" : "Correlations"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {selectedNode && (
            <>
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 rounded-full" style={{ backgroundColor: selectedNode.data.color }} />
                <span className="font-medium">{selectedNode.data.label}</span>
              </div>
              <Badge variant="outline" className="capitalize">{selectedNode.data.nodeType}</Badge>
              {selectedNode.data.status && (
                <p className="text-sm text-muted-foreground">
                  Status: <span className="capitalize text-foreground">{selectedNode.data.status}</span>
                </p>
              )}
              {["policy", "dlp", "mcp", "gateway"].includes(selectedNode.id) &&
                (bindingPolicies.length > 0 ? bindingPolicies : linkedPolicies).length > 0 && (
                <div className="space-y-2 border-t border-border pt-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {selectedBinding ? `Policies — ${selectedBinding.bundle_name ?? selectedBinding.name}` : "Linked policies"}
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
                          Open in Policy Studio
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
                  <p>{selectedBinding.policies.length} policies across {selectedBinding.graph_node_ids.length} graph stages</p>
                </div>
              )}
              {selectedNode.id === "gateway" && gatewayStatus && (
                <div className="space-y-1 border-t border-border pt-3 text-sm">
                  <p>Requests today: {gatewayStatus.requests_today.toLocaleString()}</p>
                  <p>Blocked today: {gatewayStatus.blocked_today.toLocaleString()}</p>
                  <p>Upstream: {gatewayStatus.proxy_mode ?? "mock"}</p>
                </div>
              )}
            </>
          )}

          <div className="space-y-2 border-t border-border pt-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {selectedNode || selectedEdge ? "Related flows" : "All governance flows"}
            </p>
            {correlations.map((c) => (
              <div key={`${c.from}-${c.to}-${c.label}`} className="rounded-md border border-border/60 bg-muted/10 p-2 text-xs">
                <div className="flex items-center gap-1 font-medium">
                  <span>{c.from}</span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <span>{c.to}</span>
                  <Badge variant="outline" className="ml-auto text-[10px]">{c.label}</Badge>
                </div>
                <p className="mt-1 text-muted-foreground">{c.detail}</p>
              </div>
            ))}
          </div>

          {!selectedNode && !selectedEdge && (
            <p className="text-xs text-muted-foreground">
              Solid lines = governance request path. Dashed purple lines = LLM model routing. Click a node or line for details.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
