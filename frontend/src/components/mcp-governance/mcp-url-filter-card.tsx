"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { GlobeLock, Loader2, Search } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiError, type ApiMcpUrlFilterSettings } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50";

const vendors = ["none", "zscaler", "fortigate", "cisco", "custom"];

export function McpUrlFilterCard({ canEdit }: { canEdit: boolean }) {
  const token = useAuthStore((s) => s.token);
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["mcp-url-filters", token],
    queryFn: () => api.getMcpUrlFilters(token!),
    enabled: Boolean(token),
  });
  const [form, setForm] = useState<ApiMcpUrlFilterSettings | null>(null);
  const [patternsText, setPatternsText] = useState("");
  const [vendorKey, setVendorKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [probeUrl, setProbeUrl] = useState("https://example.com");
  const [probeResult, setProbeResult] = useState<string | null>(null);

  useEffect(() => {
    if (!data) return;
    setForm(data);
    setPatternsText(data.patterns.join("\n"));
  }, [data]);

  async function save() {
    if (!token || !canEdit || !form) return;
    setError(null);
    setSaving(true);
    try {
      await api.updateMcpUrlFilters(token, {
        ...form,
        patterns: patternsText.split("\n").map((line) => line.trim()).filter(Boolean),
        vendor_api_key: vendorKey || undefined,
      });
      setVendorKey("");
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save URL filters");
    } finally {
      setSaving(false);
    }
  }

  async function runProbe() {
    if (!token) return;
    setError(null);
    setProbeResult(null);
    try {
      const result = await api.probeMcpUrlFilter(token, probeUrl);
      setProbeResult(`${result.allowed ? "Allowed" : "Blocked"} — ${result.host} (${result.mode})`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Probe failed");
    }
  }

  if (isLoading || !form) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading URL filter policy…
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <GlobeLock className="h-4 w-4 text-amber-400" />
          Web search & URL filters
        </CardTitle>
        <CardDescription>
          Control fetch and web-search MCP tools with tenant allow/deny patterns and optional Zscaler, FortiGate, or
          Cisco classification hooks.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant={form.enabled ? "success" : "secondary"}>{form.enabled ? "Enabled" : "Disabled"}</Badge>
          <Badge variant="outline">{form.mode}</Badge>
          {form.vendor !== "none" && <Badge variant="outline">{form.vendor}</Badge>}
          {form.vendor_configured && <Badge variant="outline">Vendor key set</Badge>}
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">Mode</span>
            <select
              className={inputClass}
              disabled={!canEdit}
              value={form.mode}
              onChange={(e) => setForm({ ...form, mode: e.target.value })}
            >
              <option value="denylist">Denylist</option>
              <option value="allowlist">Allowlist</option>
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">Vendor hook</span>
            <select
              className={inputClass}
              disabled={!canEdit}
              value={form.vendor}
              onChange={(e) => setForm({ ...form, vendor: e.target.value })}
            >
              {vendors.map((vendor) => (
                <option key={vendor} value={vendor}>
                  {vendor}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">Host patterns (one per line)</span>
          <textarea
            className={`${inputClass} min-h-[96px] py-2`}
            disabled={!canEdit}
            value={patternsText}
            onChange={(e) => setPatternsText(e.target.value)}
          />
        </label>

        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">Vendor endpoint URL</span>
          <input
            className={inputClass}
            disabled={!canEdit}
            value={form.vendor_endpoint}
            onChange={(e) => setForm({ ...form, vendor_endpoint: e.target.value })}
            placeholder="https://security.example.com/url-classify"
          />
        </label>

        {canEdit && (
          <label className="block space-y-1 text-sm">
            <span className="text-muted-foreground">Vendor API key (optional, vault-backed)</span>
            <input
              className={inputClass}
              type="password"
              value={vendorKey}
              onChange={(e) => setVendorKey(e.target.value)}
              placeholder={form.vendor_configured ? "Leave blank to keep existing key" : "Bearer token for vendor hook"}
            />
          </label>
        )}

        <div className="flex flex-wrap gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              disabled={!canEdit}
              checked={form.enabled}
              onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
            />
            Policy enabled
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              disabled={!canEdit}
              checked={form.block_private_ips}
              onChange={(e) => setForm({ ...form, block_private_ips: e.target.checked })}
            />
            Block private IPs
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              disabled={!canEdit}
              checked={form.web_search_enabled}
              onChange={(e) => setForm({ ...form, web_search_enabled: e.target.checked })}
            />
            Allow web search tools
          </label>
        </div>

        <div className="flex flex-wrap items-end gap-2">
          <label className="flex-1 space-y-1 text-sm">
            <span className="text-muted-foreground">Probe URL</span>
            <input className={inputClass} value={probeUrl} onChange={(e) => setProbeUrl(e.target.value)} />
          </label>
          <Button variant="outline" size="sm" className="gap-2" onClick={runProbe}>
            <Search className="h-4 w-4" />
            Probe
          </Button>
          {canEdit && (
            <Button size="sm" disabled={saving} onClick={save}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save policy"}
            </Button>
          )}
        </div>

        {probeResult && <p className="text-sm text-muted-foreground">{probeResult}</p>}
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
