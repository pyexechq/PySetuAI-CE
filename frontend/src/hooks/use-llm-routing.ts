"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { RoutingModel, RoutingRule } from "@/lib/mock-data";
import { useAuthStore } from "@/stores/auth-store";

const EMPTY_MODELS: RoutingModel[] = [];
const EMPTY_RULES: RoutingRule[] = [];

const modelColors: Record<string, string> = {
  "GPT-4o": "#3b82f6",
  "Gemini 1.5 Pro": "#8b5cf6",
  "Claude 3.5 Sonnet": "#f97316",
  "Llama 3.1 70B": "#22c55e",
};

function mapProvider(m: Awaited<ReturnType<typeof api.getLlmProviders>>[0]): RoutingModel {
  return {
    id: m.id,
    model: m.model,
    providerType: m.provider_type,
    endpointUrl: m.endpoint_url ?? null,
    requests: m.requests,
    percentage: m.percentage,
    latency: m.latency,
    successRate: m.success_rate,
    isActive: m.is_active,
    apiKeySet: m.api_key_set,
    apiKeyMasked: m.api_key_masked,
    costPer1mInput: m.cost_per_1m_input ?? 0,
    costPer1mOutput: m.cost_per_1m_output ?? 0,
    color: modelColors[m.model] ?? "#6366f1",
  };
}

export function useLlmRouting() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const modelsQuery = useQuery({
    queryKey: ["llm-providers", token],
    queryFn: () => api.getLlmProviders(token!).then((data) => data.map(mapProvider)),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const rulesQuery = useQuery({
    queryKey: ["routing-rules", token],
    queryFn: () =>
      api.getRoutingRules(token!).then((data) =>
        data.map(
          (r): RoutingRule => ({
            id: r.id,
            name: r.name,
            priority: r.priority,
            condition: r.condition,
            targetModel: r.target_model,
            status: r.status as RoutingRule["status"],
            responseFormat: r.response_format ?? "auto",
          })
        )
      ),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  function invalidateProviders() {
    queryClient.invalidateQueries({ queryKey: ["llm-providers"] });
    queryClient.invalidateQueries({ queryKey: ["integrations"] });
  }

  function invalidateRules() {
    queryClient.invalidateQueries({ queryKey: ["routing-rules"] });
  }

  return {
    models: modelsQuery.data ?? EMPTY_MODELS,
    rules: rulesQuery.data ?? EMPTY_RULES,
    isLoading: modelsQuery.isLoading || rulesQuery.isLoading,
    invalidateProviders,
    invalidateRules,
  };
}
