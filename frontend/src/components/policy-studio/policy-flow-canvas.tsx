"use client";

import { useCallback, useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ArrowRight, Plus } from "lucide-react";
import type { PolicyRule } from "@/lib/mock-data";
import type { PolicyGraphLink } from "@/lib/policy-graph-map";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  policyFlowNodeTypes,
  type PolicyBlockNodeData,
  type PolicyRuleNodeData,
} from "@/components/policy-studio/policy-rule-node";

const INGRESS_ID = "__ingress__";
const ENFORCE_ID = "__enforce__";
const NODE_X = 60;
const START_Y = 0;
const ROW_HEIGHT = 130;

const edgeStyle = { stroke: "#94a3b8", strokeWidth: 2 };

const blockColors = {
  ingress: "#6366f1",
  enforce: "#8b5cf6",
};

function buildPolicyFlowGraph(
  rules: PolicyRule[],
  graphLink: PolicyGraphLink | null,
  selectedRuleId: string | null
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [
    {
      id: INGRESS_ID,
      type: "policyBlock",
      position: { x: NODE_X, y: START_Y },
      draggable: false,
      selectable: false,
      data: {
        blockType: "ingress",
        label: "Request Ingress",
        subtitle: "Incoming prompts and tool calls enter the policy pipeline",
        color: blockColors.ingress,
      } satisfies PolicyBlockNodeData,
    },
  ];

  rules.forEach((rule, index) => {
    nodes.push({
      id: rule.id,
      type: "policyRule",
      position: { x: NODE_X, y: START_Y + (index + 1) * ROW_HEIGHT },
      draggable: true,
      data: {
        rule,
        index,
        selected: selectedRuleId === rule.id,
      } satisfies PolicyRuleNodeData,
    });
  });

  const enforceY = START_Y + (rules.length + 1) * ROW_HEIGHT;
  nodes.push({
    id: ENFORCE_ID,
    type: "policyBlock",
    position: { x: NODE_X, y: enforceY },
    draggable: false,
    selectable: false,
    data: {
      blockType: "enforce",
      label: graphLink?.graph_node_label ?? "Policy Enforce",
      subtitle: graphLink?.edge_labels.join(" → ") ?? "Apply matched rule actions",
      color: blockColors.enforce,
    } satisfies PolicyBlockNodeData,
  });

  const chain = [INGRESS_ID, ...rules.map((r) => r.id), ENFORCE_ID];
  const edges: Edge[] = chain.slice(0, -1).map((source, i) => {
    const target = chain[i + 1];
    const isFirst = source === INGRESS_ID;
    const isLast = target === ENFORCE_ID;
    const label = isFirst ? "ingress" : isLast ? "enforce" : "evaluate";

    return {
      id: `${source}-${target}`,
      source,
      target,
      type: "smoothstep",
      label,
      animated: rules.find((r) => r.id === source)?.enabled !== false,
      markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8", width: 16, height: 16 },
      style: edgeStyle,
      labelStyle: { fill: "#64748b", fontSize: 11, fontWeight: 600 },
      labelBgStyle: { fill: "#ffffff", fillOpacity: 0.95 },
      labelBgPadding: [6, 4] as [number, number],
      labelBgBorderRadius: 4,
    };
  });

  return { nodes, edges };
}

function snapRuleNodes(nodes: Node[], ruleIds: string[]): Node[] {
  const idToIndex = new Map(ruleIds.map((id, i) => [id, i]));
  return nodes.map((node) => {
    const index = idToIndex.get(node.id);
    if (index === undefined || node.type !== "policyRule") return node;
    return {
      ...node,
      position: { x: NODE_X, y: START_Y + (index + 1) * ROW_HEIGHT },
      data: { ...(node.data as PolicyRuleNodeData), index },
    };
  });
}

export function PolicyFlowCanvas({
  rules,
  graphLink,
  selectedRuleId,
  onRuleSelect,
  onRuleReorder,
  onEditRule,
  onAddRule,
  canEdit = false,
}: {
  rules: PolicyRule[];
  graphLink: PolicyGraphLink | null;
  selectedRuleId: string | null;
  onRuleSelect: (ruleId: string | null) => void;
  onRuleReorder: (ruleIds: string[]) => void;
  onEditRule: (rule: PolicyRule) => void;
  onAddRule?: () => void;
  canEdit?: boolean;
}) {
  const graph = useMemo(
    () => buildPolicyFlowGraph(rules, graphLink, selectedRuleId),
    [rules, graphLink, selectedRuleId]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph.edges);

  useEffect(() => {
    setNodes(graph.nodes);
    setEdges(graph.edges);
  }, [graph, setNodes, setEdges]);

  const selectedRule = rules.find((r) => r.id === selectedRuleId) ?? null;

  const handleNodeDragStop = useCallback(() => {
    setNodes((current) => {
      const ruleNodes = current.filter((n) => n.type === "policyRule");
      const sorted = [...ruleNodes].sort((a, b) => a.position.y - b.position.y);
      const newOrder = sorted.map((n) => n.id);
      const prevOrder = rules.map((r) => r.id);
      const changed = newOrder.some((id, i) => id !== prevOrder[i]);
      if (changed) {
        onRuleReorder(newOrder);
      }
      return snapRuleNodes(current, newOrder);
    });
  }, [rules, onRuleReorder, setNodes]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (node.type !== "policyRule") return;
      onRuleSelect(node.id);
    },
    [onRuleSelect]
  );

  return (
    <div className="grid gap-4 lg:grid-cols-4">
      <div className="lg:col-span-3 overflow-hidden rounded-lg border border-border/60">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-muted/10 px-3 py-2">
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{rules.length} rules</Badge>
            <Badge variant="secondary">{rules.filter((r) => r.enabled).length} active</Badge>
          </div>
          <p className="text-xs text-muted-foreground">Drag rule nodes to reorder evaluation sequence</p>
        </div>
        <div className="relative h-[480px] w-full pysetu-flow">
          {rules.length === 0 && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-background/80 p-6 text-center backdrop-blur-[1px]">
              <p className="text-sm font-medium">No rules in this policy yet</p>
              <p className="mt-1 max-w-sm text-xs text-muted-foreground">
                Switch to List view or use Add Rule above to define conditions and actions. Drag-and-drop ordering
                appears here once rules exist.
              </p>
              {onAddRule && (
                <Button variant="outline" size="sm" className="mt-4 gap-1.5" onClick={onAddRule} disabled={!canEdit}>
                  <Plus className="h-3.5 w-3.5" />
                  Add Rule
                </Button>
              )}
            </div>
          )}
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onNodeDragStop={handleNodeDragStop}
            onPaneClick={() => onRuleSelect(null)}
            nodeTypes={policyFlowNodeTypes}
            nodesDraggable
            nodesConnectable={false}
            fitView
            fitViewOptions={{ padding: 0.25 }}
            minZoom={0.4}
            maxZoom={1.25}
            defaultEdgeOptions={{ type: "smoothstep", style: edgeStyle }}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={16} size={1} color="#e2e8f0" />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      </div>

      <div className="space-y-3 rounded-lg border border-border/60 bg-muted/10 p-4">
        <p className="text-sm font-medium">{selectedRule ? "Rule Details" : "Policy Flow"}</p>
        {selectedRule ? (
          <>
            <div className="space-y-1">
              <p className="font-medium">{selectedRule.name}</p>
              <p className="font-mono text-xs text-muted-foreground">{selectedRule.condition}</p>
            </div>
            <div className="flex flex-wrap gap-1">
              <Badge variant="outline">{selectedRule.action}</Badge>
              <Badge variant="outline" className="capitalize">
                {selectedRule.severity}
              </Badge>
              {!selectedRule.enabled && <Badge variant="outline">Disabled</Badge>}
            </div>
            <Button variant="outline" size="sm" className="w-full" onClick={() => onEditRule(selectedRule)}>
              Edit Rule
            </Button>
          </>
        ) : rules.length === 0 ? (
          <>
            <p className="text-xs text-muted-foreground">
              No rules yet. Add a rule to build the evaluation pipeline from ingress to enforcement.
            </p>
            {onAddRule && (
              <Button variant="outline" size="sm" className="w-full gap-1.5" onClick={onAddRule} disabled={!canEdit}>
                <Plus className="h-3.5 w-3.5" />
                Add Rule
              </Button>
            )}
          </>
        ) : (
          <>
            <p className="text-xs text-muted-foreground">
              Rules evaluate top-to-bottom. Click a rule node for details, or drag to change priority.
            </p>
            {graphLink && (
              <div className="rounded-md border border-border/60 bg-card/50 p-2 text-xs">
                <div className="flex items-center gap-1 font-medium">
                  <span>Ingress</span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <span>{graphLink.graph_node_label}</span>
                </div>
                <p className="mt-1 text-muted-foreground">{graphLink.description}</p>
              </div>
            )}
            <div className="space-y-1.5">
              {rules.map((rule, i) => (
                <button
                  key={rule.id}
                  type="button"
                  onClick={() => onRuleSelect(rule.id)}
                  className="flex w-full items-center gap-2 rounded-md border border-border/60 bg-card/50 px-2 py-1.5 text-left text-xs hover:bg-muted/40"
                >
                  <span className="font-bold text-muted-foreground">{i + 1}</span>
                  <span className="truncate">{rule.name}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
