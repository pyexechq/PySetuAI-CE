import type { GovernanceEdge, GovernanceNode } from "@/lib/types/domain";

/** Static layout positions for the governance graph canvas — not sample metrics. */
export const governanceNodes: GovernanceNode[] = [
  { id: "gateway", label: "AI Gateway", type: "gateway", x: 400, y: 40, color: "#6366f1" },
  { id: "router", label: "LLM Router", type: "router", x: 400, y: 140, color: "#3b82f6" },
  { id: "policy", label: "Policy Engine", type: "policy", x: 200, y: 240, color: "#8b5cf6" },
  { id: "dlp", label: "DLP Scanner", type: "dlp", x: 600, y: 240, color: "#22c55e" },
  { id: "mcp", label: "MCP Broker", type: "mcp", x: 400, y: 340, color: "#f97316" },
  { id: "gpt4", label: "GPT-4o", type: "model", x: 150, y: 440, color: "#3b82f6" },
  { id: "claude", label: "Claude 3.5", type: "model", x: 350, y: 440, color: "#f97316" },
  { id: "gemini", label: "Gemini 1.5", type: "model", x: 550, y: 440, color: "#8b5cf6" },
  { id: "audit", label: "Audit Log", type: "audit", x: 650, y: 140, color: "#ef4444" },
];

export const governanceEdges: GovernanceEdge[] = [
  { from: "gateway", to: "router", label: "ingress", correlation: "All client requests enter through the AI Gateway" },
  { from: "router", to: "policy", label: "inspect", correlation: "LLM Router sends prompts to Policy Engine for rule checks" },
  { from: "router", to: "dlp", label: "scan", correlation: "Parallel DLP scan for PII and data classification" },
  { from: "policy", to: "mcp", label: "enforce", correlation: "Approved tool calls flow through MCP Broker" },
  { from: "dlp", to: "mcp", label: "redact", correlation: "Redacted content forwarded to MCP layer" },
  { from: "gateway", to: "audit", label: "log", correlation: "Every gateway event is written to Audit Log" },
  { from: "router", to: "audit", label: "trace", correlation: "Routing decisions recorded for observability" },
];
