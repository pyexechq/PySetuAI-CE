"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiMcpServer } from "@/lib/api";
import type { McpServer } from "@/lib/types/domain";
import { useAuthStore } from "@/stores/auth-store";

function mapServer(s: ApiMcpServer): McpServer {
  return {
    id: s.id,
    name: s.name,
    category: s.category,
    successRate: s.success_rate,
    avgLatency: s.avg_latency,
    totalCalls: s.total_calls,
    status: s.status as McpServer["status"],
    tools: s.tools,
    toolNames: s.tool_names ?? [],
    endpointUrl: s.endpoint_url,
    transport: s.transport ?? "sse",
    connectionConfig: s.connection_config ?? {},
    trustScore: s.trust_score,
    riskScore: s.risk_score,
  };
}

export function useMcpServers() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["mcp-servers", token],
    queryFn: () => api.getMcpServers(token!).then((data) => data.map(mapServer)),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  function invalidateMcpServers() {
    queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
  }

  return { ...query, invalidateMcpServers };
}
