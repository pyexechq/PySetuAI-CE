"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { KeyRound, Loader2, RefreshCw, Save, Trash2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50";

export function McpOAuthBrokerCard({ canEdit }: { canEdit: boolean }) {
  const token = useAuthStore((s) => s.token);
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["mcp-oauth", token],
    queryFn: () => api.getMcpOAuthList(token!),
    enabled: Boolean(token),
  });

  const servers = data?.servers ?? [];
  const [serverId, setServerId] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [grantType, setGrantType] = useState("client_credentials");
  const [tokenUrl, setTokenUrl] = useState("");
  const [clientId, setClientId] = useState("");
  const [scopes, setScopes] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = servers.find((item) => item.server_id === serverId) ?? servers[0];

  useEffect(() => {
    if (!selected) return;
    setServerId(selected.server_id);
    setEnabled(selected.enabled);
    setGrantType(selected.grant_type || "client_credentials");
    setTokenUrl(selected.token_url || "");
    setClientId(selected.client_id || "");
    setScopes(selected.scopes || "");
    setClientSecret("");
    setRefreshToken("");
    setAccessToken("");
  }, [selected?.server_id, selected?.configured, selected?.grant_type, selected?.token_url, selected?.client_id]);

  async function save() {
    if (!token || !canEdit || !serverId) return;
    setError(null);
    setSaving(true);
    try {
      await api.upsertMcpOAuth(token, serverId, {
        enabled,
        grant_type: grantType,
        token_url: tokenUrl,
        client_id: clientId,
        scopes,
        client_secret: clientSecret || undefined,
        refresh_token: refreshToken || undefined,
        access_token: accessToken || undefined,
      });
      setClientSecret("");
      setRefreshToken("");
      setAccessToken("");
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save OAuth credentials");
    } finally {
      setSaving(false);
    }
  }

  async function refresh() {
    if (!token || !canEdit || !serverId) return;
    setError(null);
    setRefreshing(true);
    try {
      await api.refreshMcpOAuth(token, serverId);
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Token refresh failed");
    } finally {
      setRefreshing(false);
    }
  }

  async function remove() {
    if (!token || !canEdit || !serverId) return;
    if (!window.confirm("Remove OAuth credentials for this MCP server?")) return;
    setError(null);
    try {
      await api.deleteMcpOAuth(token, serverId);
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove OAuth credentials");
    }
  }

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading OAuth broker…
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <KeyRound className="h-4 w-4 text-sky-400" />
          OAuth token broker
        </CardTitle>
        <CardDescription>
          Store MCP client secrets in the {data?.secrets_backend ?? "database"} backend. The gateway injects a fresh
          Bearer token on health checks, discovery, and multiplex tool calls.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-red-400">{error}</p>}
        {servers.length === 0 ? (
          <p className="text-sm text-muted-foreground">Register an MCP server first, then attach OAuth credentials.</p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <select
                className={`${inputClass} max-w-sm`}
                value={serverId}
                onChange={(event) => setServerId(event.target.value)}
              >
                {servers.map((item) => (
                  <option key={item.server_id} value={item.server_id}>
                    {item.server_name}
                  </option>
                ))}
              </select>
              {selected?.configured ? (
                <Badge variant={selected.token_fresh ? "success" : "outline"}>
                  {selected.token_fresh ? "Token fresh" : "Needs refresh"}
                </Badge>
              ) : (
                <Badge variant="outline">Not configured</Badge>
              )}
              {selected?.has_client_secret && <Badge variant="outline">Secret stored</Badge>}
            </div>
            {canEdit && (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
                  Broker enabled
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">Grant type</span>
                  <select className={inputClass} value={grantType} onChange={(event) => setGrantType(event.target.value)}>
                    <option value="client_credentials">Client credentials</option>
                    <option value="refresh_token">Refresh token</option>
                    <option value="static">Static access token</option>
                  </select>
                </label>
                <label className="space-y-1 text-sm sm:col-span-2">
                  <span className="text-muted-foreground">Token URL</span>
                  <input
                    className={inputClass}
                    value={tokenUrl}
                    onChange={(event) => setTokenUrl(event.target.value)}
                    placeholder="https://idp.example/oauth/token"
                    disabled={grantType === "static"}
                  />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">Client ID</span>
                  <input className={inputClass} value={clientId} onChange={(event) => setClientId(event.target.value)} />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">Scopes</span>
                  <input className={inputClass} value={scopes} onChange={(event) => setScopes(event.target.value)} />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">
                    Client secret {selected?.has_client_secret ? "(stored — leave blank to keep)" : ""}
                  </span>
                  <input
                    className={inputClass}
                    type="password"
                    value={clientSecret}
                    onChange={(event) => setClientSecret(event.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">
                    Refresh token {selected?.has_refresh_token ? "(stored — leave blank to keep)" : ""}
                  </span>
                  <input
                    className={inputClass}
                    type="password"
                    value={refreshToken}
                    onChange={(event) => setRefreshToken(event.target.value)}
                    autoComplete="off"
                    disabled={grantType === "client_credentials"}
                  />
                </label>
                {grantType === "static" && (
                  <label className="space-y-1 text-sm sm:col-span-2">
                    <span className="text-muted-foreground">Access token</span>
                    <input
                      className={inputClass}
                      type="password"
                      value={accessToken}
                      onChange={(event) => setAccessToken(event.target.value)}
                      autoComplete="off"
                    />
                  </label>
                )}
              </div>
            )}
            {canEdit && (
              <div className="flex flex-wrap gap-2">
                <Button size="sm" className="gap-1.5" disabled={saving || !serverId} onClick={save}>
                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                  Save credentials
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5"
                  disabled={refreshing || !selected?.configured || grantType === "static"}
                  onClick={refresh}
                >
                  {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  Refresh token
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5"
                  disabled={!selected?.configured}
                  onClick={remove}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Remove
                </Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
