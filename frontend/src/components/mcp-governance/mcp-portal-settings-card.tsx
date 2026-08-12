"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Globe, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useMcpServers } from "@/hooks/use-mcp-servers";

export function McpPortalSettingsCard({ canEdit }: { canEdit: boolean }) {
  const token = useAuthStore((s) => s.token);
  const { data: settings, isLoading, refetch } = useQuery({
    queryKey: ["mcp-portal-settings", token],
    queryFn: () => api.getMcpPortalSettings(token!),
    enabled: Boolean(token) && canEdit,
  });
  const { data: servers = [], invalidateMcpServers } = useMcpServers();
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function togglePortal(enabled: boolean) {
    if (!token || !canEdit) return;
    setError(null);
    setSaving("portal");
    try {
      await api.updateMcpPortalSettings(token, enabled);
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update portal settings");
    } finally {
      setSaving(null);
    }
  }

  async function toggleServerVisibility(serverId: string, visible: boolean) {
    if (!token || !canEdit) return;
    setError(null);
    setSaving(serverId);
    try {
      await api.updateMcpServerPortalVisibility(token, serverId, visible);
      invalidateMcpServers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update visibility");
    } finally {
      setSaving(null);
    }
  }

  if (!canEdit) return null;

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading portal settings…
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Globe className="h-4 w-4 text-violet-400" />
          Self-service MCP portal
        </CardTitle>
        <CardDescription>
          Let end users browse published integrations and connect personal tokens at{" "}
          <span className="font-mono text-xs">/mcp-portal</span>.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between gap-3 rounded-md border border-border/60 p-3">
          <div>
            <p className="text-sm font-medium">Portal enabled</p>
            <p className="text-xs text-muted-foreground">Developers can open the MCP portal when enabled.</p>
          </div>
          <Button
            variant={settings?.enabled ? "default" : "outline"}
            size="sm"
            disabled={saving === "portal"}
            onClick={() => togglePortal(!settings?.enabled)}
          >
            {saving === "portal" ? <Loader2 className="h-4 w-4 animate-spin" /> : settings?.enabled ? "Enabled" : "Disabled"}
          </Button>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium">Per-server visibility</p>
          {servers.map((server) => {
            const visible = server.connectionConfig?.portal_visible !== false;
            return (
              <div
                key={server.id}
                className="flex items-center justify-between gap-3 rounded-md border border-border/60 px-3 py-2"
              >
                <span className="text-sm">{server.name}</span>
                <Button
                  variant={visible ? "outline" : "ghost"}
                  size="sm"
                  disabled={saving === server.id}
                  onClick={() => toggleServerVisibility(server.id, !visible)}
                >
                  {saving === server.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : visible ? (
                    "Published"
                  ) : (
                    "Hidden"
                  )}
                </Button>
              </div>
            );
          })}
        </div>
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
