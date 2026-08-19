"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PolicyRule, PolicyTreeNode } from "@/lib/types/domain";
import { useAuthStore } from "@/stores/auth-store";

function mapTree(nodes: import("@/lib/api").ApiPolicyTreeNode[]): PolicyTreeNode[] {
  return nodes.map((n) => ({
    id: n.id,
    label: n.label,
    type: n.type as PolicyTreeNode["type"],
    status: n.status as PolicyTreeNode["status"],
    children: n.children ? mapTree(n.children) : undefined,
  }));
}

export function usePolicyTree() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["policy-tree", token],
    queryFn: () => api.getPolicyTree(token!).then(mapTree),
    enabled: Boolean(token),
    staleTime: 60_000,
  });

  function invalidatePolicyTree() {
    queryClient.invalidateQueries({ queryKey: ["policy-tree"] });
  }

  return { ...query, invalidatePolicyTree };
}

export function usePolicyRules(policyId?: string, bundleId?: string, defaultBundle?: boolean) {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["policy-rules", token, policyId, bundleId, defaultBundle],
    queryFn: () =>
      api.getPolicyRules(token!, policyId, bundleId, defaultBundle).then((data) =>
        data.map(
          (r): PolicyRule => ({
            id: r.id,
            name: r.name,
            condition: r.condition,
            action: r.action,
            severity: r.severity as PolicyRule["severity"],
            enabled: r.enabled,
          })
        )
      ),
    enabled: Boolean(token),
    staleTime: 60_000,
  });

  function invalidatePolicyRules() {
    queryClient.invalidateQueries({ queryKey: ["policy-rules"] });
  }

  return { ...query, invalidatePolicyRules };
}
