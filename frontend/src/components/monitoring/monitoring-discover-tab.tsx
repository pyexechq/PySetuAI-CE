import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Monitor, Search, User, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type ApiSecurityEvent } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

interface DiscoveredTool {
  name: string;
  source: string;
  vendor: string;
  agent_type: string;
}

export function MonitoringDiscoverTab() {
  const token = useAuthStore((s) => s.token);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});

  const { data: events = [], isLoading, isError } = useQuery({
    queryKey: ["security-events", "tool.discover", token],
    queryFn: () => api.getSecurityEvents(token!, 200, "tool.discover"),
    enabled: Boolean(token),
  });

  const toggleGroup = (key: string) => {
    setCollapsedGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading discovery events…</p>;
  }

  if (isError) {
    return (
      <p className="rounded-lg border border-border/60 bg-muted/10 px-6 py-8 text-center text-sm text-muted-foreground">
        Could not load endpoint discovery events.
      </p>
    );
  }

  // Deduplicate tools per hostname and find the latest scan time
  const hostSummaries = events.reduce((acc, event) => {
    const hostname = event.endpoint?.hostname || "Unknown Endpoint";
    if (!acc[hostname]) {
      acc[hostname] = {
        latestScan: new Date(0),
        latestRisk: event.risk_score || 0,
        tools: new Map<string, DiscoveredTool>(),
      };
    }

    const eventDate = new Date(event.created_at);
    if (eventDate > acc[hostname].latestScan) {
      acc[hostname].latestScan = eventDate;
      acc[hostname].latestRisk = event.risk_score || 0;
    }

    const discovered = (event.metadata_json?.discovered as DiscoveredTool[]) || [];
    discovered.forEach((tool) => {
      const key = `${tool.name}-${tool.source}`;
      if (!acc[hostname].tools.has(key)) {
        acc[hostname].tools.set(key, tool);
      }
    });

    return acc;
  }, {} as Record<string, { latestScan: Date; latestRisk: number; tools: Map<string, DiscoveredTool> }>);

  const endpointCount = Object.keys(hostSummaries).length;
  let toolCount = 0;
  Object.values(hostSummaries).forEach((summary) => {
    toolCount += summary.tools.size;
  });

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Endpoint Tool Discoveries</CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant="outline">{endpointCount} endpoints</Badge>
          <Badge variant="outline">{toolCount} unique tools</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {endpointCount === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No discovery events recorded</p>
        ) : (
          Object.entries(hostSummaries).map(([hostname, summary]) => {
            const isCollapsed = collapsedGroups[hostname];
            const uniqueTools = Array.from(summary.tools.values());
            
            return (
              <div key={hostname} className="rounded-xl border border-border/60 bg-background/50 overflow-hidden shadow-sm">
                <button
                  onClick={() => toggleGroup(hostname)}
                  className="flex w-full items-center justify-between border-b border-border/60 bg-muted/30 px-4 py-3 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Monitor className="h-4 w-4 text-muted-foreground" />
                    <span className="font-semibold">{hostname}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">
                      Last scan: {summary.latestScan.toLocaleString()}
                    </span>
                    <Badge variant="secondary" className="text-xs">
                      {uniqueTools.length} {uniqueTools.length === 1 ? 'tool' : 'tools'}
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
                  <div className="p-4 bg-background">
                    {uniqueTools.length === 0 ? (
                      <p className="text-sm italic text-muted-foreground">No AI tools detected in any scans.</p>
                    ) : (
                      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        {uniqueTools.map((tool, idx) => (
                          <div key={idx} className="flex flex-col gap-2 rounded-lg border border-border/60 bg-card p-4 shadow-sm transition-colors hover:bg-muted/10">
                            <div className="flex items-center justify-between">
                              <span className="font-medium">{tool.name}</span>
                              <Badge variant="secondary" className="text-[10px] uppercase tracking-wider">{tool.vendor}</Badge>
                            </div>
                            <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                              <Search className="h-3.5 w-3.5 shrink-0" />
                              <span className="truncate">source: {tool.source}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
