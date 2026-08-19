"use client";

import { useQuery } from "@tanstack/react-query";
import { FileJson, Loader2, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AuditLogEntry } from "@/lib/types/domain";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { usePreferencesStore } from "@/stores/preferences-store";
import { formatDateTime } from "@/lib/date-utils";

interface RequestLogPanelProps {
  entry: AuditLogEntry | null;
}

function JsonBlock({ label, value }: { label: string; value: unknown }) {
  if (value == null) return null;
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <pre className="max-h-64 overflow-auto rounded-md border border-border/60 bg-muted/30 p-3 text-xs">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

export function RequestLogPanel({ entry }: RequestLogPanelProps) {
  const token = useAuthStore((s) => s.token);
  const timezone = usePreferencesStore((s) => s.timezone);
  const auditId = entry?.id;
  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit-log-body", token, auditId],
    queryFn: () => api.getAuditLogBody(token!, auditId!),
    enabled: Boolean(token && auditId && entry?.has_request_log),
  });

  if (!entry) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="text-base">Request / response log</CardTitle>
          <CardDescription>Select an audit row to inspect retained gateway payloads.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!entry.has_request_log) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="text-base">Request / response log</CardTitle>
          <CardDescription>No full payload retained for this entry (non-gateway or legacy audit).</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{entry.details}</p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading request log…
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="text-base">Request / response log</CardTitle>
          <CardDescription>Failed to load retained payload.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const ingressEvents = data.guardrail_events?.ingress as { allowed?: boolean } | undefined;
  const ingressBlocked = ingressEvents?.allowed === false;

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileJson className="h-4 w-4 text-violet-400" />
            Request / response log
          </CardTitle>
          <CardDescription>
            {entry.actor} · {entry.action} · retained {data.created_at ? formatDateTime(data.created_at, timezone) : "recently"}
          </CardDescription>
        </div>
        {ingressBlocked && (
          <Badge variant="destructive" className="gap-1">
            <ShieldAlert className="h-3 w-3" />
            Guardrail block
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <JsonBlock label="Request payload" value={data.request_payload} />
        <JsonBlock label="Response payload" value={data.response_payload} />
        <JsonBlock label="Guardrail events" value={data.guardrail_events} />
        {data.tool_events && data.tool_events.length > 0 && (
          <JsonBlock label="Tool events" value={data.tool_events} />
        )}
      </CardContent>
    </Card>
  );
}
