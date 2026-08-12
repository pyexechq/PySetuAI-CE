"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, Loader2, Search } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50";

const AGENT_SLUGS = ["claude", "openai", "gemini", "cursor", "unknown"];

export function McpAgentTogglesCard({ canEdit }: { canEdit: boolean }) {
  const token = useAuthStore((s) => s.token);
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["mcp-agent-settings", token],
    queryFn: () => api.getMcpAgentSettings(token!),
    enabled: Boolean(token),
  });
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [probeUa, setProbeUa] = useState("Claude-User anthropic-ai/0.1");
  const [probeResult, setProbeResult] = useState<string | null>(null);

  async function toggleAgent(slug: string, enabled: boolean) {
    if (!token || !canEdit) return;
    setError(null);
    setSaving(`agent:${slug}`);
    try {
      const toggles: Record<string, boolean> = {};
      for (const agent of data?.agents ?? []) {
        toggles[agent.slug] = agent.slug === slug ? enabled : agent.enabled;
      }
      await api.updateMcpAgentSettings(token, toggles);
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update agent toggle");
    } finally {
      setSaving(null);
    }
  }

  async function toggleServerAgent(serverId: string, slug: string, checked: boolean) {
    if (!token || !canEdit) return;
    const server = data?.servers.find((item) => item.server_id === serverId);
    if (!server) return;
    setError(null);
    setSaving(`server:${serverId}`);
    const next = new Set(server.allowed_agents);
    if (checked) next.add(slug);
    else next.delete(slug);
    try {
      await api.updateMcpServerAllowedAgents(token, serverId, Array.from(next));
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update server allowlist");
    } finally {
      setSaving(null);
    }
  }

  async function runDetect() {
    if (!token) return;
    setError(null);
    setProbeResult(null);
    try {
      const result = await api.detectMcpAgent(token, { user_agent: probeUa });
      setProbeResult(`${result.label} (${result.agent}) — MCP ${result.mcp_enabled ? "enabled" : "blocked"}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Detection failed");
    }
  }

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading agent MCP settings…
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Bot className="h-4 w-4 text-sky-400" />
          Agent MCP access
        </CardTitle>
        <CardDescription>
          Auto-detect Claude, OpenAI, Gemini, and Cursor clients from User-Agent or request metadata. Disable MCP
          tools for agents that should not reach your catalog.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="flex flex-wrap gap-2">
          {(data?.agents ?? []).map((agent) => (
            <div key={agent.slug} className="flex items-center gap-2 rounded-lg border border-border/60 px-3 py-2">
              <span className="text-sm">{agent.label}</span>
              {canEdit ? (
                <input
                  type="checkbox"
                  checked={agent.enabled}
                  disabled={saving === `agent:${agent.slug}`}
                  onChange={(event) => toggleAgent(agent.slug, event.target.checked)}
                />
              ) : (
                <Badge variant={agent.enabled ? "success" : "outline"}>
                  {agent.enabled ? "On" : "Off"}
                </Badge>
              )}
            </div>
          ))}
        </div>
        <div className="space-y-2 rounded-lg border border-dashed border-border/60 p-3">
          <p className="text-sm font-medium">Detection probe</p>
          <input className={inputClass} value={probeUa} onChange={(event) => setProbeUa(event.target.value)} />
          <Button size="sm" variant="outline" className="gap-1.5" onClick={runDetect}>
            <Search className="h-3.5 w-3.5" />
            Test detection
          </Button>
          {probeResult && <p className="text-xs text-muted-foreground">{probeResult}</p>}
        </div>
        {(data?.servers ?? []).length > 0 && (
          <div className="space-y-3">
            <p className="text-sm font-medium">Per-server allowlists</p>
            <p className="text-xs text-muted-foreground">
              Leave all unchecked on a server to allow every enabled agent. Check specific agents to restrict access.
            </p>
            {data?.servers.map((server) => (
              <div key={server.server_id} className="rounded-lg border border-border/60 p-3">
                <p className="text-sm font-medium">{server.server_name}</p>
                <div className="mt-2 flex flex-wrap gap-3">
                  {AGENT_SLUGS.map((slug) => {
                    const label = data?.agents.find((item) => item.slug === slug)?.label ?? slug;
                    const checked = server.allowed_agents.includes(slug);
                    return (
                      <label key={slug} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={!canEdit || saving === `server:${server.server_id}`}
                          onChange={(event) => toggleServerAgent(server.server_id, slug, event.target.checked)}
                        />
                        {label}
                      </label>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
