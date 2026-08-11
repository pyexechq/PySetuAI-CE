"use client";

import { useState } from "react";
import { Activity, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { McpServerModal } from "@/components/mcp-governance/mcp-server-modal";
import { useMcpServers } from "@/hooks/use-mcp-servers";
import { api, ApiError, type ApiMcpServer } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

const statusVariant = {
  healthy: "success" as const,
  degraded: "warning" as const,
  offline: "destructive" as const,
};

export function McpGovernanceView() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";

  const [category, setCategory] = useState("All");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<ApiMcpServer | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [checkingAll, setCheckingAll] = useState(false);
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [discoveringId, setDiscoveringId] = useState<string | null>(null);

  const { data: servers = [], isLoading, invalidateMcpServers } = useMcpServers();
  const categories = ["All", ...Array.from(new Set(servers.map((s) => s.category)))];
  const filtered = category === "All" ? servers : servers.filter((s) => s.category === category);
  const healthyCount = servers.filter((s) => s.status === "healthy").length;
  const avgSuccess = servers.length > 0 ? servers.reduce((sum, s) => sum + s.successRate, 0) / servers.length : 0;

  function openCreateModal() {
    setEditingServer(null);
    setModalOpen(true);
  }

  function openEditModal(server: (typeof servers)[0]) {
    setEditingServer({
      id: server.id,
      name: server.name,
      category: server.category,
      success_rate: server.successRate,
      avg_latency: server.avgLatency,
      total_calls: server.totalCalls,
      status: server.status,
      tools: server.tools,
      tool_names: server.toolNames,
      trust_score: server.trustScore,
      risk_score: server.riskScore,
      endpoint_url: server.endpointUrl,
      transport: server.transport,
      connection_config: server.connectionConfig,
    });
    setModalOpen(true);
  }

  async function removeServer(server: (typeof servers)[0]) {
    if (!token) return;
    if (!window.confirm(`Remove MCP server "${server.name}" from inventory?`)) return;

    setActionError(null);
    try {
      await api.deleteMcpServer(token, server.id);
      invalidateMcpServers();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to remove MCP server");
    }
  }

  async function runHealthCheck(server: (typeof servers)[0]) {
    if (!token) return;

    setActionError(null);
    setCheckingId(server.id);
    try {
      const result = await api.checkMcpServerHealth(token, server.id);
      invalidateMcpServers();
      if (!result.ok && !result.skipped) {
        setActionError(`${server.name}: ${result.message}`);
      }
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Health check failed");
    } finally {
      setCheckingId(null);
    }
  }

  async function discoverTools(server: (typeof servers)[0]) {
    if (!token) return;

    setActionError(null);
    setDiscoveringId(server.id);
    try {
      const result = await api.discoverMcpServerTools(token, server.id);
      invalidateMcpServers();
      if (!result.ok && !result.skipped) {
        setActionError(`${server.name}: ${result.message}`);
      }
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Tool discovery failed");
    } finally {
      setDiscoveringId(null);
    }
  }

  async function runAllHealthChecks() {
    if (!token) return;

    setActionError(null);
    setCheckingAll(true);
    try {
      const batch = await api.checkAllMcpServersHealth(token);
      invalidateMcpServers();
      const failed = batch.results.filter((r) => !r.ok && !r.skipped);
      if (failed.length > 0) {
        setActionError(
          `${failed.length} server(s) need attention: ${failed.map((r) => r.server_name).join(", ")}`
        );
      }
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Health checks failed");
    } finally {
      setCheckingAll(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Register MCP servers and tool catalogs. Use health checks and tool discovery to establish live MCP sessions.
        </p>
        {canEdit && (
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5"
              disabled={checkingAll || servers.length === 0}
              onClick={runAllHealthChecks}
            >
              <Activity className={`h-4 w-4 ${checkingAll ? "animate-pulse" : ""}`} />
              {checkingAll ? "Checking…" : "Run health checks"}
            </Button>
            <Button size="sm" className="gap-1.5" onClick={openCreateModal}>
              <Plus className="h-4 w-4" />
              Add MCP Server
            </Button>
          </div>
        )}
      </div>

      {actionError && <p className="text-sm text-red-400">{actionError}</p>}

      <div className="grid gap-4 sm:grid-cols-4">
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">MCP Servers</p>
            <p className="text-2xl font-bold">{servers.length}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Healthy</p>
            <p className="text-2xl font-bold text-emerald-400">{healthyCount}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Avg Success Rate</p>
            <p className="text-2xl font-bold">{avgSuccess.toFixed(1)}%</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Total Tool Calls</p>
            <p className="text-2xl font-bold">{formatNumber(servers.reduce((s, m) => s + m.totalCalls, 0))}</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex gap-4">
        <Card className="w-48 shrink-0 border-border/60 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Categories</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 pt-0">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategory(cat)}
                className={cn(
                  "w-full rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-muted/60",
                  category === cat && "bg-primary/10 text-primary"
                )}
              >
                {cat}
              </button>
            ))}
          </CardContent>
        </Card>

        <Card className="flex-1 border-border/60 bg-card/50">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
            <CardTitle>MCP Inventory</CardTitle>
            {!canEdit && (
              <p className="text-xs text-muted-foreground">Tenant Admin or Security Admin required to edit</p>
            )}
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="py-8 text-center text-sm text-muted-foreground">Loading MCP servers…</p>
            ) : filtered.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-sm text-muted-foreground">No MCP servers registered</p>
                {canEdit && (
                  <Button size="sm" className="mt-3 gap-1.5" onClick={openCreateModal}>
                    <Plus className="h-4 w-4" />
                    Add your first server
                  </Button>
                )}
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-3 font-medium">Server</th>
                    <th className="pb-3 font-medium">Category</th>
                    <th className="pb-3 font-medium text-right">Calls</th>
                    <th className="pb-3 font-medium text-right">Success</th>
                    <th className="pb-3 font-medium text-right">Latency</th>
                    <th className="pb-3 font-medium text-right">Tools</th>
                    <th className="pb-3 font-medium">Status</th>
                    {canEdit && <th className="pb-3 text-right font-medium">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((server) => (
                    <tr key={server.id} className="border-b border-border/50 last:border-0">
                      <td className="py-3">
                        <p className="font-medium">{server.name}</p>
                        {server.toolNames.length > 0 && (
                          <p className="mt-0.5 text-xs text-muted-foreground">{server.toolNames.join(", ")}</p>
                        )}
                        {server.connectionConfig?.mcp_session?.state === "initialized" && (
                          <p className="mt-0.5 text-xs text-emerald-400/80">
                            MCP session active
                            {server.connectionConfig.mcp_session.initialized_at
                              ? ` · ${new Date(server.connectionConfig.mcp_session.initialized_at).toLocaleString()}`
                              : ""}
                          </p>
                        )}
                      </td>
                      <td className="py-3 text-muted-foreground">{server.category}</td>
                      <td className="py-3 text-right">{formatNumber(server.totalCalls)}</td>
                      <td className="py-3 text-right">{server.successRate}%</td>
                      <td className="py-3 text-right">{server.avgLatency}ms</td>
                      <td className="py-3 text-right">{server.tools}</td>
                      <td className="py-3">
                        <Badge variant={statusVariant[server.status]}>{server.status}</Badge>
                      </td>
                      {canEdit && (
                        <td className="py-3">
                          <div className="flex justify-end gap-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0"
                              aria-label={`Health check ${server.name}`}
                              disabled={checkingId === server.id || checkingAll}
                              onClick={() => runHealthCheck(server)}
                            >
                              <Activity
                                className={`h-3.5 w-3.5 ${checkingId === server.id ? "animate-pulse text-primary" : ""}`}
                              />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0"
                              aria-label={`Discover tools for ${server.name}`}
                              disabled={discoveringId === server.id || server.transport === "stdio"}
                              onClick={() => discoverTools(server)}
                            >
                              <Search
                                className={`h-3.5 w-3.5 ${discoveringId === server.id ? "animate-pulse text-primary" : ""}`}
                              />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0"
                              aria-label={`Edit ${server.name}`}
                              onClick={() => openEditModal(server)}
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-red-400 hover:text-red-400"
                              aria-label={`Remove ${server.name}`}
                              onClick={() => removeServer(server)}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>

      <McpServerModal
        open={modalOpen}
        server={editingServer}
        token={token}
        categorySuggestions={categories.filter((c) => c !== "All")}
        onClose={() => setModalOpen(false)}
        onSaved={invalidateMcpServers}
      />
    </div>
  );
}
