"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function useComplianceFrameworks() {
  const token = useAuthStore((s) => s.token);

  return useQuery({
    queryKey: ["compliance-frameworks", token],
    queryFn: () => api.getComplianceFrameworks(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });
}
