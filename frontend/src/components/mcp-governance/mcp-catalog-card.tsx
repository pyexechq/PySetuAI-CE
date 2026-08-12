"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Library, Loader2, Plus } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiError, type ApiMcpCatalogEntry } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50";

export function McpCatalogCard({
  canEdit,
  onInstalled,
}: {
  canEdit: boolean;
  onInstalled: () => void;
}) {
  const token = useAuthStore((s) => s.token);
  const [installing, setInstalling] = useState<string | null>(null);
  const [customName, setCustomName] = useState("");
  const [customUrl, setCustomUrl] = useState("");
  const [customTransport, setCustomTransport] = useState("sse");
  const [savingCustom, setSavingCustom] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["mcp-catalog", token],
    queryFn: () => api.getMcpCatalog(token!),
    enabled: Boolean(token),
  });

  const entries = data?.entries ?? [];
  const categories = useMemo(
    () => ["All", ...Array.from(new Set(entries.map((entry) => entry.category)))],
    [entries],
  );
  const [category, setCategory] = useState("All");
  const filtered = category === "All" ? entries : entries.filter((entry) => entry.category === category);

  async function install(entry: ApiMcpCatalogEntry) {
    if (!token || !canEdit) return;
    setError(null);
    setInstalling(entry.slug);
    try {
      await api.installMcpCatalogEntry(token, entry.slug);
      await refetch();
      onInstalled();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Install failed");
    } finally {
      setInstalling(null);
    }
  }

  async function installCustom() {
    if (!token || !canEdit) return;
    setError(null);
    setSavingCustom(true);
    try {
      await api.installCustomMcpServer(token, {
        name: customName,
        endpoint_url: customUrl,
        transport: customTransport,
        category: "Custom",
      });
      setCustomName("");
      setCustomUrl("");
      await refetch();
      onInstalled();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Custom install failed");
    } finally {
      setSavingCustom(false);
    }
  }

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading MCP catalog…
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Library className="h-4 w-4 text-sky-400" />
          MCP catalog
        </CardTitle>
        <CardDescription>
          Curated servers with one-click install. Add a custom MCP by transport URL if it is not in the library.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="flex flex-wrap gap-2">
          {categories.map((item) => (
            <Button
              key={item}
              size="sm"
              variant={category === item ? "default" : "outline"}
              className="h-7"
              onClick={() => setCategory(item)}
            >
              {item}
            </Button>
          ))}
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {filtered.map((entry) => (
            <div
              key={entry.slug}
              className="flex flex-col gap-3 rounded-lg border border-border/60 bg-muted/10 p-4 transition-colors duration-200 hover:border-border"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium">{entry.name}</p>
                  <p className="text-xs text-muted-foreground">{entry.vendor || "Community"}</p>
                </div>
                <div className="flex flex-wrap justify-end gap-1">
                  <Badge variant="outline">{entry.category}</Badge>
                  <Badge variant="outline">{entry.transport}</Badge>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">{entry.description}</p>
              {entry.tool_names.length > 0 && (
                <p className="text-xs text-muted-foreground">Tools: {entry.tool_names.slice(0, 4).join(", ")}</p>
              )}
              {canEdit ? (
                <Button
                  size="sm"
                  variant={entry.installed ? "outline" : "default"}
                  className="gap-1.5 self-start"
                  disabled={entry.installed || installing === entry.slug}
                  onClick={() => install(entry)}
                >
                  {installing === entry.slug ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : entry.installed ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : (
                    <Plus className="h-3.5 w-3.5" />
                  )}
                  {entry.installed ? "Installed" : "Install"}
                </Button>
              ) : entry.installed ? (
                <p className="text-xs text-emerald-400">Installed</p>
              ) : null}
            </div>
          ))}
        </div>
        {canEdit && (
          <div className="space-y-3 rounded-lg border border-dashed border-border/60 p-4">
            <p className="text-sm font-medium">Custom MCP via transport URL</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="text-muted-foreground">Name</span>
                <input
                  className={inputClass}
                  value={customName}
                  onChange={(event) => setCustomName(event.target.value)}
                  placeholder="Internal wiki"
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-muted-foreground">Transport</span>
                <select
                  className={inputClass}
                  value={customTransport}
                  onChange={(event) => setCustomTransport(event.target.value)}
                >
                  <option value="sse">SSE</option>
                  <option value="streamable_http">Streamable HTTP</option>
                  <option value="stdio">Stdio</option>
                </select>
              </label>
            </div>
            <label className="block space-y-1 text-sm">
              <span className="text-muted-foreground">Endpoint URL</span>
              <input
                className={inputClass}
                value={customUrl}
                onChange={(event) => setCustomUrl(event.target.value)}
                placeholder="https://mcp.internal.example/sse"
              />
            </label>
            <Button
              size="sm"
              className="gap-1.5"
              disabled={savingCustom || !customName.trim() || !customUrl.trim()}
              onClick={installCustom}
            >
              {savingCustom ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Add custom server
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
