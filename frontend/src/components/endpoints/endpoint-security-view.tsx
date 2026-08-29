"use client";

import { useQuery } from "@tanstack/react-query";
import { Loader2, Monitor } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, type ApiEndpoint } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

function EndpointSecurityViewInner() {
  const token = useAuthStore((s) => s.token);
  const { data: endpoints = [], isLoading } = useQuery({
    queryKey: ["endpoints", token],
    queryFn: () => api.getEndpoints(token!),
    enabled: Boolean(token),
  });

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
      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-4 sm:p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between w-full min-w-0">
          <div className="space-y-2.5 w-full min-w-0 max-w-xl">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Endpoint DLP Hook Active
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <Monitor className="h-3.5 w-3.5 text-primary" />
                Zero-Trust Fleet Monitor
              </Badge>
            </div>

            <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-foreground break-words">
              Protected Endpoints & Host Telemetry
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Real-time posture and telemetry for developer workstations, remote servers, and edge nodes running the PySetu endpoint agent daemon.
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-3 gap-2.5 sm:gap-3 w-full lg:w-auto shrink-0">
            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Protected</div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-foreground">{endpoints.length}</p>
              <p className="text-[10px] text-muted-foreground">Total hosts</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-emerald-500">Online</div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-emerald-600 dark:text-emerald-400">{online}</p>
              <p className="text-[10px] text-muted-foreground">Healthy agents</p>
            </div>

            <div className="w-full rounded-xl border border-border/80 bg-card/80 p-3 sm:p-3.5 shadow-xs backdrop-blur-sm">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-500">Degraded</div>
              <p className="mt-1.5 text-lg sm:text-xl font-bold text-amber-600 dark:text-amber-400">{degraded}</p>
              <p className="text-[10px] text-muted-foreground">Needs attention</p>
            </div>
          </div>
        </div>
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

export function EndpointSecurityView() {
  return <EndpointSecurityViewInner />;
}
