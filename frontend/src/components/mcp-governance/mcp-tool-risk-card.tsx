"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { EyeOff, Loader2, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiError, type ApiMcpToolRiskItem } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const riskVariant = {
  read: "success" as const,
  write: "warning" as const,
  destructive: "destructive" as const,
};

export function McpToolRiskCard({ canEdit }: { canEdit: boolean }) {
  const token = useAuthStore((s) => s.token);
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["mcp-tool-risk", token],
    queryFn: () => api.getMcpToolRisk(token!),
    enabled: Boolean(token),
  });
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const tools = data?.tools ?? [];

  async function setAutoHide(enabled: boolean) {
    if (!token || !canEdit) return;
    setError(null);
    setSaving("settings");
    try {
      await api.updateMcpToolRiskSettings(token, { auto_hide_destructive: enabled });
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update auto-hide");
    } finally {
      setSaving(null);
    }
  }

  async function toggleHidden(tool: ApiMcpToolRiskItem) {
    if (!token || !canEdit) return;
    setError(null);
    setSaving(`${tool.server_id}:${tool.name}`);
    try {
      await api.updateMcpServerToolRisk(token, tool.server_id, {
        tools: [{ name: tool.name, hidden: !tool.hidden }],
      });
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update tool visibility");
    } finally {
      setSaving(null);
    }
  }

  async function setRisk(tool: ApiMcpToolRiskItem, risk: string) {
    if (!token || !canEdit) return;
    setError(null);
    setSaving(`${tool.server_id}:${tool.name}:risk`);
    try {
      await api.updateMcpServerToolRisk(token, tool.server_id, {
        tools: [{ name: tool.name, risk }],
      });
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update tool risk");
    } finally {
      setSaving(null);
    }
  }

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading tool risk taxonomy…
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldAlert className="h-4 w-4 text-sky-400" />
          Tool risk taxonomy
        </CardTitle>
        <CardDescription>
          Classify MCP tools as read, write, or destructive. Hidden tools are omitted from multiplex lists, dynamic
          tool calling, and invoke.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            {data?.visible_count ?? 0} visible · {data?.hidden_count ?? 0} hidden
          </p>
          {canEdit && (
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={Boolean(data?.auto_hide_destructive)}
                disabled={saving === "settings"}
                onChange={(event) => setAutoHide(event.target.checked)}
              />
              Auto-hide destructive tools
            </label>
          )}
        </div>
        {tools.length === 0 ? (
          <p className="text-sm text-muted-foreground">Discover tools on a server to classify them.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 font-medium">Tool</th>
                  <th className="pb-2 font-medium">Server</th>
                  <th className="pb-2 font-medium">Risk</th>
                  <th className="pb-2 font-medium">Visibility</th>
                  {canEdit && <th className="pb-2 text-right font-medium">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {tools.map((tool) => {
                  const busy = saving?.startsWith(`${tool.server_id}:${tool.name}`);
                  return (
                    <tr key={`${tool.server_id}:${tool.name}`} className="border-b border-border/50 last:border-0">
                      <td className="py-2">
                        <p className="font-medium">{tool.name}</p>
                        {tool.description && (
                          <p className="text-xs text-muted-foreground">{tool.description}</p>
                        )}
                      </td>
                      <td className="py-2 text-muted-foreground">{tool.server_name}</td>
                      <td className="py-2">
                        {canEdit ? (
                          <select
                            className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                            value={tool.risk}
                            disabled={busy}
                            onChange={(event) => setRisk(tool, event.target.value)}
                          >
                            <option value="read">read</option>
                            <option value="write">write</option>
                            <option value="destructive">destructive</option>
                          </select>
                        ) : (
                          <Badge variant={riskVariant[tool.risk as keyof typeof riskVariant] ?? "outline"}>
                            {tool.risk}
                          </Badge>
                        )}
                      </td>
                      <td className="py-2">
                        {tool.visible ? (
                          <Badge variant="outline">Visible</Badge>
                        ) : (
                          <Badge variant="destructive">
                            {tool.auto_hidden ? "Auto-hidden" : "Hidden"}
                          </Badge>
                        )}
                      </td>
                      {canEdit && (
                        <td className="py-2 text-right">
                          <Button
                            size="sm"
                            variant="outline"
                            className="gap-1.5"
                            disabled={busy}
                            onClick={() => toggleHidden(tool)}
                          >
                            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <EyeOff className="h-3.5 w-3.5" />}
                            {tool.hidden ? "Show" : "Hide"}
                          </Button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
