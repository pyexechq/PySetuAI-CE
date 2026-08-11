"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export type GovernanceNodeData = {
  label: string;
  nodeType: string;
  color: string;
  status?: string;
  detail?: string;
};

const typeLabels: Record<string, string> = {
  gateway: "Gateway",
  router: "Router",
  policy: "Policy",
  dlp: "DLP",
  mcp: "MCP",
  model: "Model",
  audit: "Audit",
};

function GovernanceNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as GovernanceNodeData;
  const statusColor =
    nodeData.status === "healthy" || nodeData.status === "active"
      ? "bg-emerald-500"
      : nodeData.status === "degraded" || nodeData.status === "review"
        ? "bg-amber-500"
        : nodeData.status === "offline" || nodeData.status === "blocked"
          ? "bg-red-500"
          : "bg-muted-foreground/40";

  return (
    <div
      className={`min-w-[120px] rounded-xl border-2 bg-card/90 px-3 py-2 shadow-lg backdrop-blur transition-shadow ${
        selected ? "border-primary shadow-primary/20" : "border-border/60"
      }`}
      style={{ borderColor: selected ? nodeData.color : undefined }}
    >
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !bg-muted-foreground" />
      <div className="flex items-center gap-2">
        <div className="h-3 w-3 rounded-full" style={{ backgroundColor: nodeData.color }} />
        <div className="min-w-0">
          <p className="truncate text-xs font-semibold">{nodeData.label}</p>
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
            {typeLabels[nodeData.nodeType] ?? nodeData.nodeType}
          </p>
        </div>
      </div>
      {nodeData.status && (
        <div className="mt-2 flex items-center gap-1.5">
          <span className={`h-1.5 w-1.5 rounded-full ${statusColor}`} />
          <span className="text-[10px] capitalize text-muted-foreground">{nodeData.status}</span>
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !bg-muted-foreground" />
    </div>
  );
}

export const GovernanceNode = memo(GovernanceNodeComponent);
