"use client";

/**
 * BL-085 — Tool-level RBAC explicit deny lists per group
 *
 * Renders a per-role deny list panel where admins can mark specific MCP tools
 * as explicitly blocked for a given user role. The deny entries are maintained
 * in frontend state and will be persisted to the backend once the deny-list API
 * endpoint is available (POST /api/v1/rbac/tool-deny-lists).
 *
 * Until the backend endpoint ships, the card shows the full UI and persists
 * deny entries in localStorage so the UX is fully functional end-to-end.
 */

import { useEffect, useMemo, useState } from "react";
import { Plus, ShieldX, Trash2, AlertCircle, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useMcpServers } from "@/hooks/use-mcp-servers";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

// ─── types ────────────────────────────────────────────────────────────────────

const ROLES = [
  { value: "tenant_admin",    label: "Tenant Admin",     color: "text-purple-400" },
  { value: "security_admin",  label: "Security Admin",   color: "text-rose-400"   },
  { value: "ai_user",         label: "AI User",          color: "text-blue-400"   },
  { value: "readonly_user",   label: "Read-Only User",   color: "text-slate-400"  },
];

interface DenyEntry {
  id: string;
  serverId: string;
  role: string;
  toolName: string;
  serverName: string;
  reason: string;
  addedAt: string;
}

// ─── component ────────────────────────────────────────────────────────────────

export function McpToolDenyListCard({ canEdit }: { canEdit: boolean }) {
  const { data: servers = [] } = useMcpServers();
  const token = useAuthStore((state) => state.token);

  const [denyList, setDenyList] = useState<DenyEntry[]>([]);
  const [selectedRole, setSelectedRole] = useState<string>(ROLES[2].value); // default: ai_user
  const [addingEntry, setAddingEntry] = useState(false);

  // Form state for new entry
  const [newTool, setNewTool] = useState("");
  const [newReason, setNewReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!token) return;
    api.getMcpToolDenyLists(token).then((entries) => setDenyList(entries.map((entry) => ({
      id: entry.id,
      role: entry.role,
      serverId: entry.server_id,
      toolName: entry.tool_name,
      serverName: entry.server_name,
      reason: entry.reason,
      addedAt: entry.created_at,
    })))).catch(() => undefined);
  }, [token]);

  // All tools across all servers, flattened
  const allToolOptions = useMemo(
    () =>
      servers.flatMap((s) =>
        (s.toolNames ?? []).map((name) => ({
          value: `${s.name}::${name}`,
          label: `${name}  (${s.name})`,
          toolName: name,
          serverName: s.name,
        }))
      ),
    [servers]
  );

  const filteredDenyList = denyList.filter((e) => e.role === selectedRole);

  function addEntry() {
    setFormError(null);
    if (!newTool) { setFormError("Select a tool to deny"); return; }
    const parsed = newTool.split("::");
    const toolName = parsed[1] ?? newTool;
    const serverName = parsed[0] ?? "—";
    const alreadyExists = denyList.some(
      (e) => e.role === selectedRole && e.toolName === toolName && e.serverName === serverName
    );
    if (alreadyExists) { setFormError("This tool is already denied for this role"); return; }

    if (!token) return;
    api.createMcpToolDenyRule(token, { role: selectedRole, server_id: servers.find((server) => server.name === serverName)?.id ?? "", tool_name: toolName, reason: newReason.trim() || "Explicit deny by admin" })
      .then((created) => {
        setDenyList((current) => [...current, {
          id: created.id,
          role: created.role,
          serverId: created.server_id,
          toolName: created.tool_name,
          serverName: created.server_name,
          reason: created.reason,
          addedAt: created.created_at,
        }]);
        setNewTool(""); setNewReason(""); setAddingEntry(false); setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      }).catch((error: Error) => setFormError(error.message));
  }

  function removeEntry(entry: DenyEntry) {
    if (!token) return;
    api.deleteMcpToolDenyRule(token, entry.id).then(() => setDenyList((current) => current.filter((candidate) => candidate.id !== entry.id))).catch(() => undefined);
  }

  const role = ROLES.find((r) => r.value === selectedRole);

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldX className="h-4 w-4 text-rose-400" />
          Tool RBAC Deny Lists
          <span className="ml-1 text-[10px] font-normal text-rose-400 border border-rose-400/30 bg-rose-400/5 rounded px-1.5 py-0.5">
            BL-085
          </span>
        </CardTitle>
        <CardDescription>
          Explicitly deny specific MCP tools for a user role. Denied tools are blocked regardless of server-level
          visibility or policy bundle settings. Deny list is enforced at the gateway tool-call layer.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Role selector tabs */}
        <div className="flex flex-wrap gap-2">
          {ROLES.map((r) => {
            const count = denyList.filter((e) => e.role === r.value).length;
            return (
              <button
                key={r.value}
                type="button"
                onClick={() => setSelectedRole(r.value)}
                className={cn(
                  "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-all",
                  selectedRole === r.value
                    ? "border-primary/60 bg-primary/5 text-foreground"
                    : "border-border/60 bg-card/50 text-muted-foreground hover:border-border/90"
                )}
              >
                <span className={r.color}>●</span>
                {r.label}
                {count > 0 && (
                  <span className="ml-1 rounded-full bg-rose-500/20 px-1.5 py-0.5 text-[10px] text-rose-400 font-semibold">
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Deny list table for selected role */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-muted-foreground">
              Denied tools for{" "}
              <span className={cn("font-semibold", role?.color)}>{role?.label}</span>
            </p>
            {canEdit && !addingEntry && (
              <Button
                size="sm"
                variant="outline"
                className="h-7 gap-1.5 text-xs border-rose-500/40 text-rose-400 hover:bg-rose-500/10"
                onClick={() => { setAddingEntry(true); setFormError(null); }}
              >
                <Plus className="h-3.5 w-3.5" /> Add deny rule
              </Button>
            )}
          </div>

          {/* Add form */}
          {addingEntry && canEdit && (
            <div className="mb-4 rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 space-y-3">
              <p className="text-xs font-semibold text-rose-400">New Deny Entry — {role?.label}</p>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium" htmlFor="deny-tool">Tool</label>
                  {allToolOptions.length > 0 ? (
                    <select
                      id="deny-tool"
                      value={newTool}
                      onChange={(e) => setNewTool(e.target.value)}
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
                    >
                      <option value="">— select tool —</option>
                      {allToolOptions.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      id="deny-tool"
                      value={newTool}
                      onChange={(e) => setNewTool(e.target.value)}
                      placeholder="tool_name"
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm font-mono outline-none"
                    />
                  )}
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium" htmlFor="deny-reason">Reason (optional)</label>
                  <input
                    id="deny-reason"
                    value={newReason}
                    onChange={(e) => setNewReason(e.target.value)}
                    placeholder="e.g. High risk — exec capability"
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
                  />
                </div>
              </div>
              {formError && (
                <p className="flex items-center gap-1.5 text-xs text-red-400">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0" /> {formError}
                </p>
              )}
              <div className="flex gap-2">
                <Button size="sm" variant="destructive" className="gap-1.5 text-xs" onClick={addEntry}>
                  <ShieldX className="h-3.5 w-3.5" /> Add deny rule
                </Button>
                <Button size="sm" variant="ghost" className="text-xs" onClick={() => { setAddingEntry(false); setFormError(null); }}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Saved feedback */}
          {saved && (
            <div className="mb-3 flex items-center gap-2 text-xs text-emerald-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Deny rule saved
            </div>
          )}

          {/* Table */}
          {filteredDenyList.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/60 py-8 text-center text-sm text-muted-foreground">
              No tools denied for {role?.label}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/60">
                  <th className="pb-3 text-left text-xs font-medium text-muted-foreground">Tool</th>
                  <th className="pb-3 text-left text-xs font-medium text-muted-foreground">Server</th>
                  <th className="pb-3 text-left text-xs font-medium text-muted-foreground">Reason</th>
                  <th className="pb-3 text-left text-xs font-medium text-muted-foreground">Added</th>
                  {canEdit && <th className="pb-3 w-8" />}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {filteredDenyList.map((entry, i) => (
                  <tr key={i} className="hover:bg-muted/30 transition-colors group">
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <ShieldX className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                        <span className="font-mono text-xs text-rose-300 font-medium">{entry.toolName}</span>
                        <Badge variant="destructive" className="text-[10px]">DENIED</Badge>
                      </div>
                    </td>
                    <td className="py-3 text-xs text-muted-foreground">{entry.serverName}</td>
                    <td className="py-3 text-xs text-muted-foreground max-w-xs truncate" title={entry.reason}>
                      {entry.reason}
                    </td>
                    <td className="py-3 text-xs text-muted-foreground tabular-nums">
                      {new Date(entry.addedAt).toLocaleDateString()}
                    </td>
                    {canEdit && (
                      <td className="py-3 text-right">
                        <button
                          type="button"
                          className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-all"
                          onClick={() => removeEntry(entry)}
                          aria-label={`Remove deny rule for ${entry.toolName}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Info note */}
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <AlertCircle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            Deny rules are enforced at the gateway tool-call layer and take precedence over all other access settings.
            Backend API endpoint (<code className="text-[11px]">POST /api/v1/rbac/tool-deny-lists</code>) is in scope for Sprint 15.
            Rules are persisted in browser storage until the endpoint ships.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
