"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useDateRangeStore } from "@/stores/date-range-store";

export function useObservability() {
  const token = useAuthStore((s) => s.token);
  const from = useDateRangeStore((s) => s.from);
  const to = useDateRangeStore((s) => s.to);
  const range = { from_date: from, to_date: to };

  const overviewQuery = useQuery({
    queryKey: ["observability-overview", token, from, to],
    queryFn: () => api.getObservabilityOverview(token!, range),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const tracesQuery = useQuery({
    queryKey: ["observability-traces", token, from, to],
    queryFn: () => api.getObservabilityTraces(token!, 20, { ...range, dlp_only: true }),
    enabled: Boolean(token),
    staleTime: 15_000,
  });

  return {
    overview: overviewQuery.data,
    traces: tracesQuery.data ?? [],
    isLoading: overviewQuery.isLoading || tracesQuery.isLoading,
    isError: overviewQuery.isError || tracesQuery.isError,
  };
}
