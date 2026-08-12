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

const WEBHOOK_TYPES = ["slack", "servicenow"] as const;

const emptyForm: ApiAlertWebhookCreateRequest = {
  name: "",
  webhook_type: "slack",
  endpoint_url: "",
  enabled: true,
};

export function AlertWebhooksPanel() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ApiAlertWebhookCreateRequest>(emptyForm);
  const [showForm, setShowForm] = useState(false);

  const { data: webhooks = [], isLoading } = useQuery({
    queryKey: ["alert-webhooks", token],
    queryFn: () => api.listAlertWebhooks(token!),
    enabled: Boolean(token),
  });

  const createMutation = useMutation({
    mutationFn: () => api.createAlertWebhook(token!, form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-webhooks"] });
      setForm(emptyForm);
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

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <Bell className="h-4 w-4" />
            Alert Webhooks
          </CardTitle>
          <CardDescription>
            Send policy violations and blocked requests to Slack or ServiceNow (stub delivery — test ping supported).
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowForm((v) => !v)} className="gap-1">
          <Plus className="h-4 w-4" />
          Add webhook
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
              placeholder={form.webhook_type === "slack" ? "https://hooks.slack.com/services/…" : "https://instance.service-now.com/api/now/table/incident"}
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
            {form.webhook_type === "servicenow" && (
              <input
                type="password"
                placeholder="OAuth / Bearer token (optional)"
                value={form.auth_token ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, auth_token: e.target.value || undefined }))}
                className="flex h-9 rounded-md border border-input bg-background px-3 text-sm"
              />
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
            Loading webhooks…
          </p>
        ) : webhooks.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No alert webhooks configured. Add a Slack incoming webhook or ServiceNow Table API endpoint.
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

  return (
    <li className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/60 p-3 text-sm">
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{hook.name}</span>
          <Badge variant="outline">{hook.webhook_type}</Badge>
          {!hook.enabled && <Badge variant="warning">Disabled</Badge>}
        </div>
        <p className="truncate text-xs text-muted-foreground">{hook.endpoint_url}</p>
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
