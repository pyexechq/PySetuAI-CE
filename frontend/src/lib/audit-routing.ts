import type { AuditLogEntry } from "@/lib/types/domain";

/** Resolve the LLM Router rule from structured metadata or legacy audit details. */
export function resolveAuditRoutingRule(entry: Pick<AuditLogEntry, "matched_routing_rule" | "routing_strategy" | "details">): {
  rule: string | null;
  label: string;
} {
  const rule =
    entry.matched_routing_rule?.trim() ||
    entry.details.match(/routing_rule=([^;]+)/)?.[1]?.trim() ||
    null;

  if (!rule) {
    return { rule: null, label: "Routing rule" };
  }

  const label = entry.routing_strategy === "routing_group" ? "Routing group" : "Routing rule";
  return { rule, label };
}
