"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Check, Copy, Loader2, Plug, Unplug } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiError, type ApiMcpPortalEntry } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50";

const statusVariant = {
  healthy: "success" as const,
  degraded: "warning" as const,
  offline: "destructive" as const,
};

const connectionVariant = {
  connected: "success" as const,
  ready: "secondary" as const,
  needs_auth: "warning" as const,
};

export function McpPortalView() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const [error, setError] = useState<string | null>(null);
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [tokenInput, setTokenInput] = useState<Record<string, string>>({});
  const [copied, setCopied] = useState(false);
  const [enabling, setEnabling] = useState(false);

  const { data, isLoading, error: queryError, refetch } = useQuery({
    queryKey: ["mcp-portal", token],
    queryFn: () => api.getMcpPortal(token!),
    enabled: Boolean(token),
  });

  const canManagePortal =
    user?.role === "tenant_admin" || user?.role === "security_admin" || user?.role === "platform_admin";

  async function connect(entry: ApiMcpPortalEntry) {
    if (!token) return;
    setError(null);
    setConnectingId(entry.server_id);
    try {
      await api.connectMcpPortalServer(token, entry.server_id, tokenInput[entry.server_id] || "");
      await refetch();
      setTokenInput((prev) => ({ ...prev, [entry.server_id]: "" }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connect failed");
    } finally {
      setConnectingId(null);
    }
  }

  async function disconnect(entry: ApiMcpPortalEntry) {
    if (!token) return;
    setError(null);
    setConnectingId(entry.server_id);
    try {
      await api.disconnectMcpPortalServer(token, entry.server_id);
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Disconnect failed");
    } finally {
      setConnectingId(null);
    }
  }

  async function enablePortal() {
    if (!token) return;
    setEnabling(true);
    setError(null);
    try {
      await api.updateMcpPortalSettings(token, true);
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to enable portal");
    } finally {
      setEnabling(false);
    }
  }

  async function copyMultiplex() {
    if (!data?.multiplex_url) return;
    await navigator.clipboard.writeText(data.multiplex_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading integrations…
        </CardContent>
      </Card>
    );
  }

  if (!data?.enabled) {
    const failed = !!queryError;
    return (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {failed && <AlertTriangle className="h-4 w-4 text-destructive" />}
            MCP portal unavailable
          </CardTitle>
          <CardDescription>
            {failed
              ? queryError instanceof ApiError
                ? queryError.message
                : "Could not load portal settings."
              : "Your administrator has disabled the self-service MCP portal for this tenant."}
          </CardDescription>
          {!failed && canManagePortal && (
            <Button
              size="sm"
              className="mt-4 w-fit gap-2"
              onClick={enablePortal}
              disabled={enabling}
            >
              {enabling && <Loader2 className="h-4 w-4 animate-spin" />}
              Enable MCP portal
            </Button>
          )}
        </CardHeader>
      </Card>
    );
  }

  const entries = data.entries ?? [];

  return (
    <div className="space-y-6">
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Plug className="h-4 w-4 text-emerald-400" />
            Gateway MCP URL
          </CardTitle>
          <CardDescription>
            Add this multiplex URL in Claude Desktop, Cursor, or any MCP client. Use your PySetu client API key as the
            bearer token.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <code className="rounded-md border border-border/60 bg-muted/40 px-3 py-2 text-xs">{data.multiplex_url}</code>
          <Button variant="outline" size="sm" className="gap-2" onClick={copyMultiplex}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? "Copied" : "Copy URL"}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {entries.length === 0 ? (
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-6 text-sm text-muted-foreground">
            No integrations are published to the portal yet. Ask your admin to install MCP servers in MCP Governance.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {entries.map((entry) => (
            <Card key={entry.server_id} className="border-border/60 bg-card/50">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-base">{entry.name}</CardTitle>
                    <CardDescription className="mt-1 line-clamp-2">
                      {entry.description || entry.category}
                    </CardDescription>
                  </div>
                  <Badge variant={statusVariant[entry.status as keyof typeof statusVariant] ?? "secondary"}>
                    {entry.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{entry.category}</Badge>
                  {entry.vendor && <Badge variant="outline">{entry.vendor}</Badge>}
                  <Badge variant={connectionVariant[entry.connection_status as keyof typeof connectionVariant] ?? "secondary"}>
                    {entry.connection_status.replace("_", " ")}
                  </Badge>
                </div>
                {entry.tool_names.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Tools: {entry.tool_names.join(", ")}
                    {entry.tool_count > entry.tool_names.length ? ` (+${entry.tool_count - entry.tool_names.length} more)` : ""}
                  </p>
                )}
                {entry.auth_required && entry.connection_status === "needs_auth" && (
                  <input
                    className={inputClass}
                    type="password"
                    placeholder="Personal access token"
                    value={tokenInput[entry.server_id] ?? ""}
                    onChange={(e) =>
                      setTokenInput((prev) => ({ ...prev, [entry.server_id]: e.target.value }))
                    }
                  />
                )}
                <div className="flex flex-wrap gap-2">
                  {entry.auth_required && entry.connection_status === "needs_auth" && (
                    <Button
                      size="sm"
                      className="gap-2"
                      disabled={connectingId === entry.server_id}
                      onClick={() => connect(entry)}
                    >
                      {connectingId === entry.server_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Plug className="h-4 w-4" />
                      )}
                      Connect
                    </Button>
                  )}
                  {entry.connection_status === "connected" && entry.auth_required && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-2"
                      disabled={connectingId === entry.server_id}
                      onClick={() => disconnect(entry)}
                    >
                      {connectingId === entry.server_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Unplug className="h-4 w-4" />
                      )}
                      Disconnect
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
