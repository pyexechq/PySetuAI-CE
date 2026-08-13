"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AuditLogEntry } from "@/lib/types/domain";
import { api, type ApiTraceSpan } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

interface TraceReplayPanelProps {
  entry: AuditLogEntry | null;
}

const statusVariant = {
  ok: "success" as const,
  allowed: "success" as const,
  review: "warning" as const,
  error: "destructive" as const,
  blocked: "destructive" as const,
};

const stageColors: Record<string, string> = {
  ingress: "bg-sky-500/70",
  transform: "bg-violet-500/70",
  routing: "bg-amber-500/70",
  upstream: "bg-emerald-500/70",
  egress: "bg-orange-500/70",
  audit: "bg-slate-500/70",
};

function SpanTimeline({ spans, totalMs }: { spans: ApiTraceSpan[]; totalMs: number }) {
  const width = Math.max(totalMs, 1);
  return (
    <div className="space-y-2">
      {spans.map((span) => {
        const barPct = Math.min(100, Math.round((span.duration_ms / width) * 100));
        const leftPct = Math.min(100, Math.round(((span.offset_ms ?? 0) / width) * 100));
        return (
          <div key={`${span.name}-${span.offset_ms ?? 0}`} className="space-y-1">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-medium">{span.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">{span.service}</span>
                <span className="tabular-nums">{span.duration_ms}ms</span>
                <Badge variant={statusVariant[span.status as keyof typeof statusVariant] ?? "outline"} className="text-[10px]">
                  {span.status}
                </Badge>
              </div>
            </div>
            <div className="relative h-2 rounded-full bg-muted/50">
              <div
                className={cn("absolute top-0 h-2 rounded-full", stageColors[span.stage ?? ""] ?? "bg-primary/60")}
                style={{ left: `${leftPct}%`, width: `${Math.max(barPct, 4)}%` }}
              />
            </div>
            {span.detail && <p className="text-xs text-muted-foreground">{span.detail}</p>}
          </div>
        );
      })}
    </div>
  );
}

export function TraceReplayPanel({ entry }: TraceReplayPanelProps) {
  const token = useAuthStore((s) => s.token);
  const auditId = entry?.id;
  const { data, isLoading, isError } = useQuery({
    queryKey: ["trace-replay", token, auditId],
    queryFn: () => api.getObservabilityTraceDetail(token!, auditId!),
    enabled: Boolean(token && auditId),
  });

  if (!entry) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="text-base">OTel trace replay</CardTitle>
          <CardDescription>Select an audit row to replay gateway stages from OpenTelemetry correlation.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Reconstructing trace…
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="text-base">OTel trace replay</CardTitle>
          <CardDescription>Unable to load trace replay for this entry.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-4 w-4 text-emerald-400" />
            OTel trace replay
          </CardTitle>
          <CardDescription>
            {data.actor} · {data.action} · {data.duration_ms}ms · {data.span_count} spans
          </CardDescription>
        </div>
        <Badge variant="outline" className="font-mono text-[10px]">
          {data.otel_trace_id ?? data.trace_id}
        </Badge>
      </CardHeader>
      <CardContent>
        <SpanTimeline spans={data.spans} totalMs={data.duration_ms} />
      </CardContent>
    </Card>
  );
}
