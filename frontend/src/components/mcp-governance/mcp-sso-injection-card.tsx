"use client";

/**
 * BL-084 — SSO Context Credential Injection
 *
 * Configures per-server OIDC token forwarding. When enabled, the gateway
 * intercepts the logged-in user's OIDC access_token (from their SSO session)
 * and injects it as an HTTP header on all downstream MCP REST calls to that
 * server — so the MCP backend sees the real user identity without the LLM
 * ever touching the credential.
 *
 * Frontend UI: Per-server toggle + header name + optional claim extraction.
 * Backend endpoint: POST /api/v1/mcp-servers/{id}/sso-injection (Sprint 14).
 * Until backend ships, config is persisted in localStorage.
 */

import { useEffect, useState } from "react";
import { CheckCircle2, KeyRound, LogIn, Save, Shield } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useMcpServers } from "@/hooks/use-mcp-servers";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

// ─── types ────────────────────────────────────────────────────────────────────

interface SsoInjectionConfig {
  serverId: string;
  enabled: boolean;
  headerName: string;       // e.g. "Authorization" or "X-User-Token"
  headerFormat: string;     // e.g. "Bearer {token}" or "{token}"
  claimExtract: string;     // e.g. "" (full token) or "sub", "email"
  updatedAt: string;
}

const INPUT_CLASS = "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-primary disabled:opacity-50";

const HEADER_FORMAT_PRESETS = [
  { value: "Bearer {token}", label: "Bearer {token}  (standard OAuth2)" },
  { value: "{token}",        label: "{token}  (raw token)" },
  { value: "Token {token}",  label: "Token {token}  (DRF style)" },
];

// ─── component ────────────────────────────────────────────────────────────────

export function McpSsoInjectionCard({ canEdit }: { canEdit: boolean }) {
  const { data: servers = [] } = useMcpServers();
  const token = useAuthStore((state) => state.token);

  const [configs, setConfigs] = useState<SsoInjectionConfig[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Form state
  const [enabled, setEnabled] = useState(false);
  const [headerName, setHeaderName] = useState("Authorization");
  const [headerFormat, setHeaderFormat] = useState("Bearer {token}");
  const [claimExtract, setClaimExtract] = useState("");

  // REST servers only (SSE / HTTP — not stdio)
  const restServers = servers.filter((s) => s.transport !== "stdio");

  useEffect(() => {
    if (restServers.length > 0 && !selectedId) {
      setSelectedId(restServers[0].id);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [restServers.length]);

  useEffect(() => {
    if (!token || !selectedId) return;
    api.getMcpSsoInjection(token, selectedId).then((config) => {
      const normalized: SsoInjectionConfig = {
        serverId: config.server_id,
        enabled: config.enabled,
        headerName: config.header_name,
        headerFormat: config.header_format,
        claimExtract: config.claim_extract,
        updatedAt: config.updated_at,
      };
      setConfigs((current) => [...current.filter((entry) => entry.serverId !== selectedId), normalized]);
    }).catch(() => undefined);
  }, [selectedId, token]);

  // Hydrate form when server selection changes
  useEffect(() => {
    if (!selectedId) return;
    const cfg = configs.find((c) => c.serverId === selectedId);
    if (cfg) {
      setEnabled(cfg.enabled);
      setHeaderName(cfg.headerName || "Authorization");
      setHeaderFormat(cfg.headerFormat || "Bearer {token}");
      setClaimExtract(cfg.claimExtract || "");
    } else {
      setEnabled(false);
      setHeaderName("Authorization");
      setHeaderFormat("Bearer {token}");
      setClaimExtract("");
    }
  }, [selectedId, configs]);

  async function saveConfig() {
    if (!selectedId || !token) return;
    setSaving(true);
    const entry: SsoInjectionConfig = {
      serverId: selectedId,
      enabled,
      headerName: headerName.trim() || "Authorization",
      headerFormat: headerFormat.trim() || "Bearer {token}",
      claimExtract: claimExtract.trim(),
      updatedAt: new Date().toISOString(),
    };
    try {
      const savedConfig = await api.updateMcpSsoInjection(token, selectedId, { enabled, header_name: entry.headerName, header_format: entry.headerFormat, claim_extract: entry.claimExtract });
      setConfigs([...configs.filter((c) => c.serverId !== selectedId), {
        serverId: savedConfig.server_id,
        enabled: savedConfig.enabled,
        headerName: savedConfig.header_name,
        headerFormat: savedConfig.header_format,
        claimExtract: savedConfig.claim_extract,
        updatedAt: savedConfig.updated_at,
      }]);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  const selectedServer = restServers.find((s) => s.id === selectedId);
  const currentCfg = configs.find((c) => c.serverId === selectedId);
  const enabledCount = configs.filter((c) => c.enabled).length;

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <LogIn className="h-4 w-4 text-indigo-400" />
          SSO Context Credential Injection
          <span className="ml-1 text-[10px] font-normal text-indigo-400 border border-indigo-400/30 bg-indigo-400/5 rounded px-1.5 py-0.5">
            BL-084
          </span>
        </CardTitle>
        <CardDescription>
          Forward the logged-in user&apos;s OIDC <code className="text-[11px]">access_token</code> as an HTTP header to
          downstream MCP REST backends — so each server sees real user identity without the LLM touching credentials.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Status summary */}
        <div className="flex flex-wrap gap-3">
          <div className="rounded-lg border border-border/60 bg-muted/20 px-4 py-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-indigo-400" />
            <div>
              <p className="text-xs text-muted-foreground">Injection Active</p>
              <p className="text-lg font-bold">{enabledCount} server{enabledCount !== 1 ? "s" : ""}</p>
            </div>
          </div>
          <div className="rounded-lg border border-border/60 bg-muted/20 px-4 py-3 flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Token Source</p>
              <p className="text-sm font-semibold">User OIDC Session</p>
            </div>
          </div>
        </div>

        {restServers.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border/60 py-8 text-center text-sm text-muted-foreground">
            No SSE/HTTP MCP servers registered. Register a remote server first.
          </div>
        ) : (
          <>
            {/* Server selector */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="sso-server">MCP Server</label>
              <div className="flex gap-2">
                <select
                  id="sso-server"
                  value={selectedId}
                  onChange={(e) => setSelectedId(e.target.value)}
                  className={cn(INPUT_CLASS, "max-w-sm")}
                >
                  {restServers.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
                {currentCfg && (
                  <Badge variant={currentCfg.enabled ? "success" : "outline"} className="self-center">
                    {currentCfg.enabled ? "Injection ON" : "Injection OFF"}
                  </Badge>
                )}
              </div>
              {selectedServer && (
                <p className="text-xs text-muted-foreground font-mono">
                  {selectedServer.endpointUrl ?? "no endpoint"} · {(selectedServer.transport ?? "sse").toUpperCase()}
                </p>
              )}
            </div>

            {/* Config fields */}
            {canEdit && (
              <div className="rounded-xl border border-border/60 bg-muted/10 p-4 space-y-4">
                <label className="flex items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(e) => setEnabled(e.target.checked)}
                    className="rounded"
                  />
                  <span className="font-medium">Enable OIDC token injection for this server</span>
                </label>

                <div className={cn("space-y-4 transition-opacity", !enabled && "opacity-40 pointer-events-none")}>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium" htmlFor="sso-header-name">Header Name</label>
                      <input
                        id="sso-header-name"
                        value={headerName}
                        onChange={(e) => setHeaderName(e.target.value)}
                        placeholder="Authorization"
                        className={INPUT_CLASS}
                      />
                      <p className="text-xs text-muted-foreground">
                        HTTP header sent to the MCP REST backend
                      </p>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium" htmlFor="sso-header-format">Header Format</label>
                      <input
                        id="sso-header-format"
                        value={headerFormat}
                        onChange={(e) => setHeaderFormat(e.target.value)}
                        placeholder="Bearer {token}"
                        className={cn(INPUT_CLASS, "font-mono text-xs")}
                        list="sso-format-presets"
                      />
                      <datalist id="sso-format-presets">
                        {HEADER_FORMAT_PRESETS.map((p) => (
                          <option key={p.value} value={p.value}>{p.label}</option>
                        ))}
                      </datalist>
                      <p className="text-xs text-muted-foreground">
                        Use <code className="text-[11px]">{"{token}"}</code> as the placeholder for the raw OIDC token value
                      </p>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium" htmlFor="sso-claim">
                      Token claim to extract{" "}
                      <span className="text-xs font-normal text-muted-foreground">(optional — leave blank for full access_token)</span>
                    </label>
                    <input
                      id="sso-claim"
                      value={claimExtract}
                      onChange={(e) => setClaimExtract(e.target.value)}
                      placeholder="sub  or  email  or  custom_claim"
                      className={cn(INPUT_CLASS, "font-mono text-xs")}
                    />
                    <p className="text-xs text-muted-foreground">
                      If set, the gateway decodes the JWT and extracts only this claim value as the injected token.
                      Useful for sending just a user ID or email to the MCP backend.
                    </p>
                  </div>
                </div>

                {/* Preview */}
                {enabled && (
                  <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3">
                    <p className="text-xs font-semibold text-indigo-400 mb-1.5">Header Preview</p>
                    <code className="text-xs text-muted-foreground font-mono">
                      {headerName || "Authorization"}: {(headerFormat || "Bearer {token}").replace(
                        "{token}",
                        claimExtract
                          ? `<user.${claimExtract}>`
                          : "<user.access_token>"
                      )}
                    </code>
                  </div>
                )}

                {/* Save button */}
                <div className="flex items-center gap-2">
                  <Button size="sm" className="gap-1.5" disabled={saving || !selectedId} onClick={saveConfig}>
                    <Save className="h-3.5 w-3.5" />
                    {saving ? "Saving…" : "Save injection config"}
                  </Button>
                  {saved && (
                    <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Saved
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Read-only view for non-admins */}
            {!canEdit && currentCfg && (
              <div className="rounded-xl border border-border/60 bg-muted/10 p-4 space-y-2">
                <p className="text-sm font-medium">{currentCfg.enabled ? "Injection enabled" : "Injection disabled"}</p>
                {currentCfg.enabled && (
                  <>
                    <p className="text-xs text-muted-foreground">
                      Header: <code className="text-[11px]">{currentCfg.headerName}</code>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Format: <code className="text-[11px]">{currentCfg.headerFormat}</code>
                    </p>
                  </>
                )}
              </div>
            )}
          </>
        )}

        {/* Sprint note */}
        <div className="flex items-start gap-2 rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3">
          <Shield className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            Gateway enforcement via{" "}
            <code className="text-[11px]">POST /api/v1/mcp-servers/{"{id}"}/sso-injection</code> is scoped to Sprint 14.
            Configuration is persisted locally until the backend endpoint ships.
            The OIDC token is sourced from the user's existing authenticated session — no additional credentials required.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
