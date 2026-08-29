"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, Loader2, ShieldAlert, Monitor, User, Search, Download } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api, type ApiAgent, type ApiEndpoint } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

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
  const [activeTab, setActiveTab] = useState<"agents" | "endpoints">("agents");

  const { data: agents = [], isLoading: agentsLoading } = useQuery({
    queryKey: ["agents", token],
    queryFn: () => api.getAgents(token!),
    enabled: Boolean(token) && activeTab === "agents",
  });

  const { data: endpoints = [], isLoading: endpointsLoading } = useQuery({
    queryKey: ["endpoints", token],
    queryFn: () => api.getEndpoints(token!),
    enabled: Boolean(token) && activeTab === "endpoints",
  });

  return (
    <div className="space-y-6">
      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-4 sm:p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between w-full min-w-0">
          <div className="space-y-2.5 w-full min-w-0 max-w-xl">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Fleet EDR Mesh Active
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <Bot className="h-3.5 w-3.5 text-primary" />
                Zero-Trust Agent Discovery
              </Badge>
              <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-xs font-mono">
                Local Sandbox Enforced
              </Badge>
            </div>

            <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-foreground break-words">
              Agent Fleet & Endpoint Inventory
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Track, govern, and enforce real-time DLP boundaries on all autonomous AI desktop agents, browser extensions, IDE copilots, and developer workstations.
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-2.5 sm:gap-3 w-full lg:w-auto shrink-0">
            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Agents</span>
                <Bot className="h-3.5 w-3.5 text-primary" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-foreground">{agents.length}</p>
              <p className="text-[10px] text-muted-foreground">Discovered entities</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Endpoints</span>
                <Monitor className="h-3.5 w-3.5 text-cyan-500" />
              </div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-foreground">{endpoints.length}</p>
              <p className="text-[10px] text-muted-foreground">Monitored machines</p>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Navigation Action Bar ────────────────────────────────────────────── */}
      <div className="flex w-full flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs">
          <button
            onClick={() => setActiveTab("agents")}
            className={cn(
              "px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all",
              activeTab === "agents"
                ? "bg-primary text-primary-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Discovered AI Agents ({agents.length})
          </button>
          <button
            onClick={() => setActiveTab("endpoints")}
            className={cn(
              "px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all",
              activeTab === "endpoints"
                ? "bg-primary text-primary-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Protected Endpoints ({endpoints.length})
          </button>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button size="sm" variant="outline" className="gap-1.5 text-xs h-8">
              <Download className="h-3.5 w-3.5" />
              Download Agent Binaries
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Endpoint Agents</DropdownMenuLabel>
            <DropdownMenuItem onClick={() => window.open("/downloads/agent-macos.zip", "_blank")}>
              macOS (Apple Silicon / Intel)
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => window.open("/downloads/agent-windows.exe", "_blank")}>
              Windows (x64)
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => window.open("/downloads/agent-linux.zip", "_blank")}>
              Linux (x64 / ARM64)
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuLabel>Browser Extensions</DropdownMenuLabel>
            <DropdownMenuItem onClick={() => window.open("/downloads/ext-chrome.crx", "_blank")}>
              Google Chrome
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => window.open("/downloads/ext-edge.crx", "_blank")}>
              Microsoft Edge
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => window.open("/downloads/ext-firefox.xpi", "_blank")}>
              Mozilla Firefox
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {activeTab === "agents" ? (
        <AgentsTab agents={agents} isLoading={agentsLoading} />
      ) : (
        <EndpointsTab endpoints={endpoints} isLoading={endpointsLoading} />
      )}
    </div>
  );
}

function riskCardClass(score: number): string {
  if (score >= 80) return "border-red-500/30 bg-red-500/5";
  if (score >= 60) return "border-amber-500/30 bg-amber-500/5";
  if (score >= 30) return "border-blue-500/30 bg-blue-500/5";
  return "border-green-500/30 bg-green-500/5";
}

function AgentsTab({ agents, isLoading }: { agents: ApiAgent[]; isLoading: boolean }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [groupBy, setGroupBy] = useState<"hostname" | "agent_type" | "vendor">("hostname");
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});

  const toggleGroup = (key: string) => {
    setCollapsedGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

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

  const groupedAgents = agents.reduce((acc, agent) => {
    let key = "Unknown";
    if (groupBy === "hostname") key = agent.endpoint?.hostname || "Unknown machine";
    if (groupBy === "agent_type") key = agent.agent_type || "Unknown type";
    if (groupBy === "vendor") key = agent.vendor || "Unknown vendor";
    
    if (!acc[key]) acc[key] = [];
    acc[key].push(agent);
    return acc;
  }, {} as Record<string, ApiAgent[]>);

  const filteredGroupKeys = Object.keys(groupedAgents).filter((key) =>
    key.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                Agent Inventory
              </CardTitle>
              <CardDescription>AI agents discovered across endpoints, dynamically grouped.</CardDescription>
            </div>
            <div className="flex flex-col sm:flex-row items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Group by:</span>
                <select
                  value={groupBy}
                  onChange={(e) => setGroupBy(e.target.value as "hostname" | "agent_type" | "vendor")}
                  className="h-8 rounded-md border border-input bg-background px-2 text-sm shadow-sm outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="hostname">Hostname</option>
                  <option value="agent_type">Agent Type</option>
                  <option value="vendor">Vendor</option>
                </select>
              </div>
              <div className="flex w-full items-center gap-2 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm sm:w-auto">
                <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search groups..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-7 w-full min-w-[200px] bg-transparent outline-none placeholder:text-muted-foreground"
                />
              </div>
            </div>
          </div>
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
          ) : filteredGroupKeys.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">No groups matching "{searchQuery}"</div>
          ) : (
            <div className="space-y-4">
              {filteredGroupKeys.map((groupKey) => {
                const isCollapsed = collapsedGroups[groupKey];
                const groupAgents = groupedAgents[groupKey];
                
                return (
                  <div key={groupKey} className="rounded-xl border border-border/60 bg-background/50 overflow-hidden shadow-sm">
                    <button
                      onClick={() => toggleGroup(groupKey)}
                      className="flex w-full items-center justify-between border-b border-border/60 bg-muted/30 px-4 py-3 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        {groupBy === "hostname" && <Monitor className="h-4 w-4 text-muted-foreground" />}
                        {groupBy === "agent_type" && <Bot className="h-4 w-4 text-muted-foreground" />}
                        {groupBy === "vendor" && <ShieldAlert className="h-4 w-4 text-muted-foreground" />}
                        <span className="font-semibold">{groupKey}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant="secondary" className="text-xs">
                          {groupAgents.length} {groupAgents.length === 1 ? 'agent' : 'agents'}
                        </Badge>
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="24"
                          height="24"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className={cn("h-4 w-4 text-muted-foreground transition-transform", isCollapsed ? "" : "rotate-180")}
                        >
                          <path d="m6 9 6 6 6-6"/>
                        </svg>
                      </div>
                    </button>
                    
                    {!isCollapsed && (
                      <div className="grid grid-cols-1 gap-4 p-4 bg-background md:grid-cols-2 2xl:grid-cols-3">
                        {groupAgents.map((agent: ApiAgent) => (
                          <div
                            key={agent.id}
                            className={cn(
                              "flex flex-col gap-3 rounded-lg border p-4 shadow-sm transition-colors",
                              riskCardClass(agent.risk_score)
                            )}
                          >
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="font-medium">{agent.name}</p>
                                <Badge variant={agent.status === "active" ? "success" : "secondary"}>{agent.status}</Badge>
                                {groupBy !== "agent_type" && (
                                  <Badge variant="outline" className="bg-background">{agent.agent_type}</Badge>
                                )}
                              </div>
                              <p className="mt-1 text-sm text-muted-foreground">
                                {agent.vendor || "Unknown vendor"}
                                {agent.version ? ` · v${agent.version}` : ""}
                              </p>
                              <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                                {groupBy !== "hostname" && (
                                  <div className="flex items-center gap-1.5">
                                    <Monitor className="h-3.5 w-3.5 shrink-0" />
                                    <span className="truncate">{agent.endpoint?.hostname || "Unknown machine"}</span>
                                  </div>
                                )}
                                <div className="flex items-center gap-1.5">
                                  <User className="h-3.5 w-3.5 shrink-0" />
                                  <span className="truncate">{agent.user_name || "Unknown user"}</span>
                                </div>
                              </div>
                              <div className="mt-3 flex flex-wrap gap-1.5">
                                {(agent.tools ?? []).slice(0, 4).map((tool, index) => (
                                  <Badge key={`${agent.id}-${index}`} variant="outline" className="text-[10px] uppercase bg-background">
                                    {tool}
                                  </Badge>
                                ))}
                                {(agent.mcp_servers ?? []).length > 0 && (
                                  <Badge variant="outline" className="text-[10px] uppercase bg-background">
                                    {agent.mcp_servers!.length} MCP
                                  </Badge>
                                )}
                              </div>
                            </div>
                            <div className="mt-2 flex items-center justify-between border-t border-border/40 pt-3">
                              <span className="text-xs text-muted-foreground">Risk Profile</span>
                              <Badge variant={riskVariant(agent.risk_score)}>
                                {riskLabel(agent.risk_score)} · {agent.risk_score}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function EndpointsTab({ endpoints, isLoading }: { endpoints: ApiEndpoint[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading endpoints…
        </CardContent>
      </Card>
    );
  }

  const online = endpoints.filter((endpoint) => endpoint.status === "online").length;
  const degraded = endpoints.filter((endpoint) => endpoint.status === "degraded").length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="text-xs text-muted-foreground">Protected endpoints</div>
            <p className="mt-1 text-2xl font-semibold">{endpoints.length}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="text-xs text-muted-foreground">Online</div>
            <p className="mt-1 text-2xl font-semibold">{online}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <div className="text-xs text-muted-foreground">Degraded</div>
            <p className="mt-1 text-2xl font-semibold">{degraded}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Monitor className="h-5 w-5" />
            Endpoints
          </CardTitle>
          <CardDescription>Devices running the PySetu endpoint agent.</CardDescription>
        </CardHeader>
        <CardContent>
          {endpoints.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
              <Monitor className="mx-auto h-8 w-8 text-muted-foreground/50" />
              <p className="mt-3 font-medium">No endpoints registered yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Register an endpoint using a client API key.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {endpoints.map((endpoint: ApiEndpoint) => (
                <div
                  key={endpoint.id}
                  className="flex flex-col gap-3 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-mono text-sm font-medium">{endpoint.hostname}</p>
                      <Badge variant={endpoint.status === "online" ? "success" : "secondary"}>
                        {endpoint.status}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {endpoint.os_name || "Unknown OS"}
                      {endpoint.os_version ? ` ${endpoint.os_version}` : ""}
                      {endpoint.agent_version ? ` · agent v${endpoint.agent_version}` : ""}
                    </p>
                  </div>
                  <p className="shrink-0 text-xs text-muted-foreground">
                    Last seen: {endpoint.last_seen_at ? new Date(endpoint.last_seen_at).toLocaleString() : "never"}
                  </p>
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
