"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { GripVertical, Shield, ArrowDownToLine, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { PolicyRule } from "@/lib/mock-data";

export type PolicyBlockNodeData = {
  blockType: "ingress" | "enforce";
  label: string;
  subtitle?: string;
  color: string;
};

export type PolicyRuleNodeData = {
  rule: PolicyRule;
  index: number;
  selected?: boolean;
};

const actionColors: Record<string, string> = {
  Block: "#ef4444",
  Redact: "#f59e0b",
  Alert: "#3b82f6",
  Allow: "#22c55e",
};

const severityVariant = {
  low: "secondary" as const,
  medium: "warning" as const,
  high: "destructive" as const,
  critical: "destructive" as const,
};

function PolicyBlockNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as PolicyBlockNodeData;
  const Icon = nodeData.blockType === "ingress" ? ArrowDownToLine : Shield;

  return (
    <div
      className={cn(
        "min-w-[180px] rounded-xl border-2 bg-card/90 px-3 py-2.5 shadow-lg backdrop-blur transition-shadow",
        selected ? "border-primary shadow-primary/20" : "border-border/60"
      )}
      style={{ borderColor: selected ? nodeData.color : undefined }}
    >
      {nodeData.blockType !== "ingress" && (
        <Handle type="target" position={Position.Top} className="!h-2 !w-2 !bg-muted-foreground" />
      )}
      <div className="flex items-center gap-2">
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
          style={{ backgroundColor: `${nodeData.color}22` }}
        >
          <Icon className="h-4 w-4" style={{ color: nodeData.color }} />
        </div>
        <div className="min-w-0">
          <p className="truncate text-xs font-semibold">{nodeData.label}</p>
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
            {nodeData.blockType === "ingress" ? "Ingress" : "Action"}
          </p>
        </div>
      </div>
      {nodeData.subtitle && (
        <p className="mt-2 text-[10px] text-muted-foreground">{nodeData.subtitle}</p>
      )}
      {nodeData.blockType !== "enforce" && (
        <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !bg-muted-foreground" />
      )}
    </div>
  );
}

function PolicyRuleNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as PolicyRuleNodeData;
  const { rule, index } = nodeData;
  const actionColor = actionColors[rule.action] ?? "#6366f1";

  return (
    <div
      className={cn(
        "min-w-[220px] max-w-[260px] rounded-xl border-2 bg-card/90 px-3 py-2.5 shadow-lg backdrop-blur transition-shadow",
        selected ? "border-primary shadow-primary/20" : "border-border/60",
        !rule.enabled && "opacity-60"
      )}
      style={{ borderColor: selected ? actionColor : undefined }}
    >
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !bg-muted-foreground" />
      <div className="flex items-start gap-2">
        <div className="mt-0.5 cursor-grab text-muted-foreground active:cursor-grabbing" title="Drag to reorder">
          <GripVertical className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-muted text-[10px] font-bold">
              {index + 1}
            </span>
            <p className="truncate text-xs font-semibold">{rule.name}</p>
          </div>
          <p className="mt-1 line-clamp-2 font-mono text-[10px] text-muted-foreground">{rule.condition}</p>
          <div className="mt-2 flex flex-wrap items-center gap-1">
            <Badge variant="outline" className="gap-1 text-[10px]">
              <Zap className="h-2.5 w-2.5" style={{ color: actionColor }} />
              {rule.action}
            </Badge>
            <Badge variant={severityVariant[rule.severity]} className="text-[10px]">
              {rule.severity}
            </Badge>
            {!rule.enabled && (
              <Badge variant="outline" className="text-[10px]">
                Disabled
              </Badge>
            )}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !bg-muted-foreground" />
    </div>
  );
}

export const PolicyBlockNode = memo(PolicyBlockNodeComponent);
export const PolicyRuleNode = memo(PolicyRuleNodeComponent);

export const policyFlowNodeTypes = {
  policyBlock: PolicyBlockNode,
  policyRule: PolicyRuleNode,
};
