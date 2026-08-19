"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Loader2, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, type ApiAgent } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

function riskVariant(score: number): "default" | "secondary" | "warning" | "destructive" | "success" | "outline" {
  if (score >= 80) return "destructive";
  if (score >= 60) return "warning";
  if (score >= 30) return "secondary";
  return "success";
}

function riskLabel(score: number): string {
  if (score >= 80) return "Critical";
  if (score >= 60) return "High";
  if (score >= 30) return "Medium";
  return "Low";
}

function AgentInventoryViewInner() {
  const token = useAuthStore((s) => s.token);
  const { data: agents = [], isLoading } = useQuery({
    queryKey: ["agents", token],
    queryFn: () => api.getAgents(token!),
    enabled: Boolean(token),
  });

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading agent inventory…
        </CardContent>
      </Card>
    );
  }

  const highRisk = agents.filter((agent) => agent.risk_score >= 60).length;
  const active = agents.filter((agent) => agent.status === "active").length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="text-xs text-muted-foreground">Discovered agents</div>
            <p className="mt-1 text-2xl font-semibold">{agents.length}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <ShieldAlert className="h-3.5 w-3.5 text-amber-500" /> High risk
            </div>
            <p className="mt-1 text-2xl font-semibold">{highRisk}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="text-xs text-muted-foreground">Active agents</div>
            <p className="mt-1 text-2xl font-semibold">{active}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Agent Inventory
          </CardTitle>
          <CardDescription>AI agents discovered across endpoints, ordered by risk.</CardDescription>
        </CardHeader>
        <CardContent>
          {agents.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
              <Bot className="mx-auto h-8 w-8 text-muted-foreground/50" />
              <p className="mt-3 font-medium">No agents discovered yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Register an endpoint agent to begin discovery.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {agents.map((agent: ApiAgent) => (
                <div
                  key={agent.id}
                  className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{agent.name}</p>
                      <Badge variant={agent.status === "active" ? "success" : "secondary"}>{agent.status}</Badge>
                      <Badge variant="outline">{agent.agent_type}</Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {agent.vendor || "Unknown vendor"}
                      {agent.version ? ` · v${agent.version}` : ""}
                      {agent.user_name ? ` · ${agent.user_name}` : ""}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(agent.tools ?? []).slice(0, 4).map((tool, index) => (
                        <Badge key={`${agent.id}-${index}`} variant="outline" className="text-xs">
                          {tool}
                        </Badge>
                      ))}
                      {(agent.mcp_servers ?? []).length > 0 && (
                        <Badge variant="outline" className="text-xs">
                          {agent.mcp_servers!.length} MCP
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge variant={riskVariant(agent.risk_score)}>
                      {riskLabel(agent.risk_score)} · {agent.risk_score}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export function AgentInventoryView() {
  return <AgentInventoryViewInner />;
}
