"use client";

import { useState } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useObservability } from "@/hooks/use-observability";
import { cn } from "@/lib/utils";
import type { ApiTraceSpan } from "@/lib/api";

const statusVariant = {
  allowed: "success" as const,
  blocked: "destructive" as const,
  review: "warning" as const,
  ok: "success" as const,
  error: "destructive" as const,
};

const stageColors: Record<string, string> = {
  ingress: "bg-sky-500/70",
  transform: "bg-violet-500/70",
  routing: "bg-amber-500/70",
  upstream: "bg-emerald-500/70",
  egress: "bg-orange-500/70",
  audit: "bg-slate-500/70",
};

function SpanRow({ span, totalMs }: { span: ApiTraceSpan; totalMs: number }) {
  const width = Math.max(totalMs, 1);
  const barPct = Math.min(100, Math.round((span.duration_ms / width) * 100));
  const leftPct = Math.min(100, Math.round(((span.offset_ms ?? 0) / width) * 100));
  return (
    <div className="space-y-1 rounded-md border border-border/40 p-2">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="font-medium">{span.name}</span>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[10px]">{span.stage ?? "stage"}</Badge>
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
      {span.detail && <p className="text-[11px] text-muted-foreground">{span.detail}</p>}
    </div>
  );
}

export function MonitoringTracesTab() {
  const { traces, isLoading } = useObservability();
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading traces…</p>;
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>OTel trace replay</CardTitle>
        <Badge variant="outline">{traces.length} traces</Badge>
      </CardHeader>
      <CardContent className="space-y-2">
        {traces.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No traces in this period</p>
        ) : (
          traces.map((trace) => (
            <div key={trace.id} className="rounded-lg border border-border/60 bg-muted/10">
              <button
                type="button"
                onClick={() => setExpandedTrace(expandedTrace === trace.id ? null : trace.id)}
                className="flex w-full items-center justify-between gap-4 p-3 text-left text-sm hover:bg-muted/20"
              >
                <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
                  <span className="font-mono text-xs text-muted-foreground">{trace.otel_trace_id ?? trace.trace_id}</span>
                  <span className="truncate">{trace.action}</span>
                  <span className="truncate text-muted-foreground">{trace.resource}</span>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge variant={statusVariant[trace.status as keyof typeof statusVariant] ?? "outline"}>
                    {trace.status}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{trace.duration_ms}ms</span>
                  <span className="text-xs text-muted-foreground">{trace.span_count} spans</span>
                </div>
              </button>
              {expandedTrace === trace.id && (
                <div className="border-t border-border/60 px-3 py-3">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                      <span>Actor: {trace.actor}</span>
                      <span>Risk: {trace.risk}</span>
                      <span>{trace.timestamp}</span>
                    </div>
                    <Button variant="outline" size="sm" className="h-7 gap-1.5 text-xs" asChild>
                      <Link
                        href={`/audit-explorer?audit_id=${encodeURIComponent(trace.id)}`}
                        title="Open this event in Audit Explorer"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Audit Explorer
                      </Link>
                    </Button>
                  </div>
                  <div className="space-y-2">
                    {trace.spans.map((span) => (
                      <SpanRow key={`${trace.id}-${span.name}-${span.offset_ms}`} span={span} totalMs={trace.duration_ms} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
