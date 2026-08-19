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

export function EndpointSecurityView() {
  return <EndpointSecurityViewInner />;
}
