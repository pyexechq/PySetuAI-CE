"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function useClientApiKeys() {
  const token = useAuthStore((s) => s.token);

  return useQuery({
    queryKey: ["client-api-keys", token],
    queryFn: () => api.getClientApiKeys(token!),
    enabled: Boolean(token),
    staleTime: 60_000,
  });
}
