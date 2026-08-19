"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Bell, Loader2, Plus, Send, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type ApiAlertWebhook, type ApiAlertWebhookCreateRequest } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { usePreferencesStore } from "@/stores/preferences-store";
import { formatDateTime } from "@/lib/date-utils";

const WEBHOOK_TYPES = ["slack", "servicenow", "bmc_helix", "datadog", "webhook"] as const;

const ENDPOINT_HINTS: Record<string, string> = {
  slack: "https://hooks.slack.com/services/...",
  servicenow: "https://instance.service-now.com/api/now/table/incident",
  bmc_helix: "https://instance/restapi/incident/create",
  datadog: "https://api.datadoghq.com",
  webhook: "https://your-endpoint.example.com/incidents",
};

const DEFAULT_DISPATCH_POLICY = {
  enabled: true,
  min_risk: "high",
  dedup_window_minutes: 15,
  on_duplicate: "update",
  allowed_sources: ["gateway", "mcp", "rag", "scanner", "audit"],
};

const emptyForm: ApiAlertWebhookCreateRequest = {
  name: "",
  webhook_type: "slack",
  endpoint_url: "",
  enabled: true,
  dispatch_policy: DEFAULT_DISPATCH_POLICY,
};

export function AlertWebhooksPanel() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ApiAlertWebhookCreateRequest>(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [configJsonText, setConfigJsonText] = useState("{}");
  const [policyJsonText, setPolicyJsonText] = useState(JSON.stringify(DEFAULT_DISPATCH_POLICY, null, 2));

  const { data: webhooks = [], isLoading } = useQuery({
    queryKey: ["alert-webhooks", token],
    queryFn: () => api.listAlertWebhooks(token!),
    enabled: Boolean(token),
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const config_json = parseJsonOrEmpty(configJsonText);
      const dispatch_policy = parseJsonOrEmpty(policyJsonText) ?? DEFAULT_DISPATCH_POLICY;
      return api.createAlertWebhook(token!, { ...form, config_json, dispatch_policy });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-webhooks"] });
      setForm(emptyForm);
      setConfigJsonText("{}");
      setPolicyJsonText(JSON.stringify(DEFAULT_DISPATCH_POLICY, null, 2));
      setShowForm(false);
    },
  });

  const testMutation = useMutation({
    mutationFn: (webhookId: string) => api.testAlertWebhook(token!, webhookId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-webhooks"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (webhookId: string) => api.deleteAlertWebhook(token!, webhookId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-webhooks"] }),
  });

  const isIncidentConnector = form.webhook_type !== "slack";

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <Bell className="h-4 w-4" />
            Incident Connectors
          </CardTitle>
          <CardDescription>
            Auto-create ITSM tickets for high/critical violations (ServiceNow, BMC Helix, Datadog, generic webhook)
            or notify Slack. Dedup updates within 15 minutes by default.
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowForm((v) => !v)} className="gap-1">
          <Plus className="h-4 w-4" />
          Add connector
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {showForm && (
          <div className="grid gap-3 rounded-md border border-border/60 p-4 sm:grid-cols-2">
            <input
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className="flex h-9 rounded-md border border-input bg-background px-3 text-sm"
            />
            <select
              value={form.webhook_type}
              onChange={(e) => setForm((f) => ({ ...f, webhook_type: e.target.value }))}
              className="flex h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              {WEBHOOK_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <input
              placeholder={ENDPOINT_HINTS[form.webhook_type] ?? "Endpoint URL"}
              value={form.endpoint_url}
              onChange={(e) => setForm((f) => ({ ...f, endpoint_url: e.target.value }))}
              className="flex h-9 rounded-md border border-input bg-background px-3 text-sm sm:col-span-2"
            />
            {form.webhook_type === "slack" && (
              <input
                placeholder="#security-alerts (optional channel override)"
                value={form.channel ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, channel: e.target.value || undefined }))}
                className="flex h-9 rounded-md border border-input bg-background px-3 text-sm"
              />
            )}
            {form.webhook_type !== "slack" && (
              <input
                type="password"
                placeholder="Bearer / API token (optional)"
                value={form.auth_token ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, auth_token: e.target.value || undefined }))}
                className="flex h-9 rounded-md border border-input bg-background px-3 text-sm"
              />
            )}
            {isIncidentConnector && (
              <>
                <textarea
                  placeholder='Connector config JSON e.g. {"assignment_group":"Security Operations"}'
                  value={configJsonText}
                  onChange={(e) => setConfigJsonText(e.target.value)}
                  rows={3}
                  className="flex min-h-[72px] rounded-md border border-input bg-background px-3 py-2 text-xs sm:col-span-2"
                />
                <textarea
                  placeholder="Dispatch policy JSON"
                  value={policyJsonText}
                  onChange={(e) => setPolicyJsonText(e.target.value)}
                  rows={4}
                  className="flex min-h-[96px] rounded-md border border-input bg-background px-3 py-2 text-xs sm:col-span-2"
                />
              </>
            )}
            <div className="flex gap-2 sm:col-span-2">
              <Button
                size="sm"
                disabled={!form.name || !form.endpoint_url || createMutation.isPending}
                onClick={() => createMutation.mutate()}
              >
                {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {isLoading ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading connectors…
          </p>
        ) : webhooks.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No incident connectors configured. Add ServiceNow, BMC Helix, a generic webhook, or Slack notifications.
          </p>
        ) : (
          <ul className="space-y-2">
            {webhooks.map((hook) => (
              <WebhookRow
                key={hook.id}
                hook={hook}
                onTest={() => testMutation.mutate(hook.id)}
                onDelete={() => deleteMutation.mutate(hook.id)}
                testing={testMutation.isPending}
              />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function WebhookRow({
  hook,
  onTest,
  onDelete,
  testing,
}: {
  hook: ApiAlertWebhook;
  onTest: () => void;
  onDelete: () => void;
  testing: boolean;
}) {
  const timezone = usePreferencesStore((s) => s.timezone);
  const minRisk = String(hook.dispatch_policy?.min_risk ?? "high");
  const dedup = Number(hook.dispatch_policy?.dedup_window_minutes ?? 15);

  return (
    <li className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/60 p-3 text-sm">
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{hook.name}</span>
          <Badge variant="outline">{hook.webhook_type}</Badge>
          {!hook.enabled && <Badge variant="warning">Disabled</Badge>}
        </div>
        <p className="truncate text-xs text-muted-foreground">{hook.endpoint_url}</p>
        {hook.webhook_type !== "slack" && (
          <p className="text-xs text-muted-foreground">
            Policy: min risk {minRisk}, dedup {dedup}m
            {hook.tickets_created ? ` · Tickets: ${hook.tickets_created}` : ""}
          </p>
        )}
        {hook.last_error && <p className="text-xs text-red-400">Last error: {hook.last_error}</p>}
        <p className="text-xs text-muted-foreground">
          Sent: {hook.alerts_sent}
          {hook.last_alert_at ? ` · Last: ${formatDateTime(hook.last_alert_at, timezone)}` : ""}
        </p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" className="gap-1" disabled={testing} onClick={onTest}>
          {testing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
          Test
        </Button>
        <Button variant="ghost" size="sm" onClick={onDelete}>
          <Trash2 className="h-4 w-4 text-red-400" />
        </Button>
      </div>
    </li>
  );
}

function parseJsonOrEmpty(text: string): Record<string, unknown> | undefined {
  const trimmed = text.trim();
  if (!trimmed) return undefined;
  try {
    const parsed = JSON.parse(trimmed);
    return typeof parsed === "object" && parsed !== null ? (parsed as Record<string, unknown>) : undefined;
  } catch {
    return undefined;
  }
}
