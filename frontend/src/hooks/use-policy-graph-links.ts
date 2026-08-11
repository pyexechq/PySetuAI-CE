"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PolicyGraphLink } from "@/lib/policy-graph-map";
import { useAuthStore } from "@/stores/auth-store";

export function usePolicyGraphLinks(nodeId?: string | null) {
  const token = useAuthStore((s) => s.token);

  return useQuery({
    queryKey: ["policy-graph-links", token, nodeId],
    queryFn: () => api.getPolicyGraphLinks(token!, nodeId ?? undefined),
    enabled: Boolean(token),
    staleTime: 60_000,
    select: (data): PolicyGraphLink[] => data,
  });
}
