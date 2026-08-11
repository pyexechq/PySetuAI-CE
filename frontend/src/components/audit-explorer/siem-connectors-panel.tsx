"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { ApiSiemConnector, ApiSiemConnectorCreateRequest } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { Loader2, Plus, Send, Trash2 } from "lucide-react";

const CONNECTOR_TYPES = ["webhook", "splunk_hec", "elastic", "azure_sentinel"] as const;
const EXPORT_FORMATS = ["json", "ndjson", "cef", "elastic_bulk"] as const;

const emptyForm: ApiSiemConnectorCreateRequest = {
  name: "",
  connector_type: "webhook",
  endpoint_url: "",
  export_format: "json",
  enabled: true,
};

export function SiemConnectorsPanel() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ApiSiemConnectorCreateRequest>(emptyForm);
  const [showForm, setShowForm] = useState(false);

  const { data: connectors = [], isLoading } = useQuery({
    queryKey: ["siem-connectors", token],
    queryFn: () => api.listSiemConnectors(token!),
    enabled: Boolean(token),
  });

  const createMutation = useMutation({
    mutationFn: () => api.createSiemConnector(token!, form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["siem-connectors"] });
      setForm(emptyForm);
      setShowForm(false);
    },
  });

  const pushMutation = useMutation({
    mutationFn: (connectorId: string) => api.pushSiemConnector(token!, connectorId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["siem-connectors"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (connectorId: string) => api.deleteSiemConnector(token!, connectorId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["siem-connectors"] }),
  });

  const exportAllMutation = useMutation({
    mutationFn: () => api.queueSiemExportAll(token!),
  });

  const handleDownload = async (format: "json" | "ndjson" | "cef") => {
    if (!token) return;
    const blob = await api.downloadAuditExport(token, format);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `audit-export.${format === "cef" ? "cef" : format === "ndjson" ? "ndjson" : "json"}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <CardTitle className="text-base">SIEM Export</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => handleDownload("json")}>
            Pull JSON
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleDownload("ndjson")}>
            Pull NDJSON
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleDownload("cef")}>
            Pull CEF
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            disabled={exportAllMutation.isPending}
            onClick={() => exportAllMutation.mutate()}
          >
            {exportAllMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            Push all
          </Button>
          <Button variant="default" size="sm" className="gap-1.5" onClick={() => setShowForm((v) => !v)}>
            <Plus className="h-3.5 w-3.5" />
            Connector
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        {showForm && (
          <div className="grid gap-3 rounded-md border border-border/60 p-4 md:grid-cols-2">
            <input
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
            <select
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={form.connector_type}
              onChange={(e) => setForm((f) => ({ ...f, connector_type: e.target.value }))}
            >
              {CONNECTOR_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
            <input
              className="md:col-span-2 rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Endpoint URL"
              value={form.endpoint_url}
              onChange={(e) => setForm((f) => ({ ...f, endpoint_url: e.target.value }))}
            />
            <input
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Auth token (optional)"
              type="password"
              value={form.auth_token ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, auth_token: e.target.value }))}
            />
            <select
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={form.export_format}
              onChange={(e) => setForm((f) => ({ ...f, export_format: e.target.value }))}
            >
              {EXPORT_FORMATS.map((fmt) => (
                <option key={fmt} value={fmt}>
                  {fmt}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              disabled={!form.name || !form.endpoint_url || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              Save connector
            </Button>
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading connectors…</p>
        ) : connectors.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No SIEM connectors configured. Add a webhook, Splunk HEC, Elastic, or Azure Sentinel endpoint.
          </p>
        ) : (
          <ul className="space-y-2">
            {connectors.map((connector: ApiSiemConnector) => (
              <li
                key={connector.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/60 px-3 py-2 text-sm"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{connector.name}</span>
                    <Badge variant="outline">{connector.connector_type}</Badge>
                    <Badge variant={connector.enabled ? "success" : "secondary"}>
                      {connector.enabled ? "enabled" : "disabled"}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground truncate max-w-xl">{connector.endpoint_url}</p>
                  <p className="text-xs text-muted-foreground">
                    Exported {connector.events_exported} · {connector.last_export_at ?? "never"}
                    {connector.last_error ? ` · error: ${connector.last_error}` : ""}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    disabled={pushMutation.isPending}
                    onClick={() => pushMutation.mutate(connector.id)}
                  >
                    <Send className="h-3.5 w-3.5" />
                    Push
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    disabled={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(connector.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
