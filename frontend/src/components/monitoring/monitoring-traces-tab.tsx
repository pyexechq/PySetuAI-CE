"use client";

import { useState } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useObservability } from "@/hooks/use-observability";
import { cn } from "@/lib/utils";

const statusVariant = {
  allowed: "success" as const,
  blocked: "destructive" as const,
  review: "warning" as const,
  ok: "success" as const,
  error: "destructive" as const,
};

export function MonitoringTracesTab() {
  const { traces, isLoading } = useObservability();
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading traces…</p>;
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Distributed traces</CardTitle>
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
                  <span className="font-mono text-xs text-muted-foreground">{trace.trace_id}</span>
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
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
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
                  <div className="space-y-1">
                    {trace.spans.map((span) => (
                      <div
                        key={`${trace.id}-${span.name}`}
                        className={cn(
                          "flex items-center gap-3 rounded-md px-2 py-1.5 text-xs",
                          span.status === "error" || span.status === "blocked"
                            ? "bg-destructive/10"
                            : "bg-background/50"
                        )}
                      >
                        <span className="w-28 font-medium">{span.name}</span>
                        <span className="flex-1 text-muted-foreground">{span.service}</span>
                        <span>{span.duration_ms}ms</span>
                        <Badge
                          variant={statusVariant[span.status as keyof typeof statusVariant] ?? "outline"}
                          className="text-[10px]"
                        >
                          {span.status}
                        </Badge>
                      </div>
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
