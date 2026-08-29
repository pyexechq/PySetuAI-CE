"use client";

import { useQuery } from "@tanstack/react-query";
import { FileJson, Loader2, ShieldAlert, ShieldCheck, Zap, AlertTriangle } from "lucide-react";
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
          <CardDescription>Select an audit row with payload retention enabled.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (!entry.has_request_log) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="text-base">Request / response log</CardTitle>
          <CardDescription>No full payload stored for this event (retention off or excluded).</CardDescription>
        </CardHeader>
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
  const classifier = data.guardrail_events?.classifier as {
    verdict?: string;
    risk_tier?: string;
    risk_score?: number;
    execution_time_micros?: number;
    matches?: Array<{ rule_name?: string; action?: string; score?: number; matched_tokens?: string[]; explanation?: string }>;
  } | undefined;

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
        <div className="flex items-center gap-2">
          {classifier && (
            <Badge variant="outline" className={`gap-1 ${classifier.verdict === "block" ? "border-rose-500/30 text-rose-400 bg-rose-500/10" : "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"}`}>
              <Zap className="h-3 w-3" />
              Classifier: {classifier.verdict?.toUpperCase()} ({classifier.risk_tier} · {classifier.execution_time_micros} μs)
            </Badge>
          )}
          {ingressBlocked && (
            <Badge variant="destructive" className="gap-1">
              <ShieldAlert className="h-3 w-3" />
              Guardrail block
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {classifier && classifier.matches && classifier.matches.length > 0 && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs space-y-2">
            <div className="flex items-center justify-between font-semibold text-amber-300">
              <span className="flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4 text-amber-400" />
                Zero-AI Deterministic Pre-Flight Guard ({classifier.matches.length} Rule Triggered)
              </span>
              <span>Score: {classifier.risk_score}/100</span>
            </div>
            <div className="space-y-1.5">
              {classifier.matches.map((m, idx) => (
                <div key={idx} className="bg-background/80 rounded p-2 border border-border/40 text-muted-foreground flex flex-col gap-1">
                  <div className="flex items-center justify-between text-foreground font-medium">
                    <span>{m.rule_name}</span>
                    <Badge variant="outline" className="text-[10px] uppercase font-mono">{m.action}</Badge>
                  </div>
                  <p className="text-[11px]">{m.explanation}</p>
                  {m.matched_tokens && m.matched_tokens.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {m.matched_tokens.map((t, tidx) => (
                        <span key={tidx} className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono text-[10px]">{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
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
