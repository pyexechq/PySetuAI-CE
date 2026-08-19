"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Workflow,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiMcpToolChainEvent, type ApiMcpToolChainSummary } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

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
  const [decisionFilter, setDecisionFilter] = useState<string>("all");

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["mcp-tool-chain-summary", token],
    queryFn: () => api.getMcpToolChainSummary(token!),
    enabled: Boolean(token),
  });

  const { data: events = [], isLoading: eventsLoading } = useQuery({
    queryKey: ["mcp-tool-chains", token, decisionFilter],
    queryFn: () => api.getMcpToolChains(token!, 200, decisionFilter),
    enabled: Boolean(token),
  });

  const { data: graph, isLoading: graphLoading } = useQuery({
    queryKey: ["mcp-tool-chain-graph", token],
    queryFn: () => api.getMcpToolChainGraph(token!, 200),
    enabled: Boolean(token),
  });

  const flowNodes: Node[] = useMemo(() => {
    if (!graph) return [];
    return graph.nodes.map((node, index) => ({
      id: node.id,
      position: { x: (index % 5) * 220, y: Math.floor(index / 5) * 160 },
      data: { label: node.label },
      style: {
        border: `1px solid ${node.color}`,
        borderRadius: 8,
        padding: "6px 10px",
        background: `${node.color}1a`,
        color: "#0f172a",
        fontSize: 12,
      },
    }));
  }, [graph]);

  const flowEdges: Edge[] = useMemo(() => {
    if (!graph) return [];
    return graph.edges.map((edge, index) => ({
      id: `e-${index}`,
      source: edge.from,
      target: edge.to,
      label: edge.label,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: edge.risk_score >= 60 ? "#ef4444" : "#94a3b8", strokeWidth: 1.5 },
      labelStyle: { fontSize: 10, fill: "#64748b" },
    }));
  }, [graph]);

  const isLoading = summaryLoading || eventsLoading || graphLoading;

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading MCP tool chains...
        </CardContent>
      </Card>
    );
  }

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
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="text-xs text-muted-foreground">Chain events</div>
            <p className="mt-1 text-2xl font-semibold">{s.total}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" /> Allowed
            </div>
            <p className="mt-1 text-2xl font-semibold">{s.allowed}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <ShieldX className="h-3.5 w-3.5 text-red-500" /> Blocked
            </div>
            <p className="mt-1 text-2xl font-semibold">{s.blocked}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Workflow className="h-3.5 w-3.5 text-amber-500" /> Awaiting approval
            </div>
            <p className="mt-1 text-2xl font-semibold">{s.approval}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <ShieldAlert className="h-3.5 w-3.5 text-amber-500" /> High risk
            </div>
            <p className="mt-1 text-2xl font-semibold">{s.high_risk}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/50">
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
          {graph && graph.nodes.length > 0 ? (
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
          {events.length === 0 ? (
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
  );
}

export function McpToolChainsView() {
  return <McpToolChainsViewInner />;
}
