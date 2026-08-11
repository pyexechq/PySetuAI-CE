"use client";

import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, Clock, ShieldAlert, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useObservability } from "@/hooks/use-observability";
import { cn, formatNumber } from "@/lib/utils";

const statusVariant = {
  allowed: "success" as const,
  blocked: "destructive" as const,
  review: "warning" as const,
  ok: "success" as const,
  error: "destructive" as const,
};

const EMPTY_OVERVIEW = {
  total_events_today: 0,
  allowed_today: 0,
  blocked_today: 0,
  under_review_today: 0,
  block_rate: 0,
  avg_latency_ms: 0,
  p95_latency_ms: 0,
  error_rate: 0,
  by_action: [] as { action: string; count: number }[],
  by_risk: [] as { risk: string; count: number }[],
  daily_trend: [] as { date: string; total: number; blocked: number }[],
};

export function ObservabilityView() {
  const { overview: overviewData, traces, isLoading } = useObservability();
  const overview = overviewData ?? EMPTY_OVERVIEW;
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null);

  if (isLoading && !overviewData) {
    return <p className="text-sm text-muted-foreground">Loading observability data…</p>;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-border/60 bg-card/50">
          <CardContent className="flex items-center gap-3 p-5">
            <div className="rounded-lg bg-indigo-500/10 p-2">
              <Activity className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Events Today</p>
              <p className="text-2xl font-bold">{formatNumber(overview.total_events_today)}</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="flex items-center gap-3 p-5">
            <div className="rounded-lg bg-emerald-500/10 p-2">
              <Zap className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Avg Latency</p>
              <p className="text-2xl font-bold">{overview.avg_latency_ms}ms</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="flex items-center gap-3 p-5">
            <div className="rounded-lg bg-amber-500/10 p-2">
              <Clock className="h-5 w-5 text-amber-400" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">P95 Latency</p>
              <p className="text-2xl font-bold">{overview.p95_latency_ms}ms</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="flex items-center gap-3 p-5">
            <div className="rounded-lg bg-red-500/10 p-2">
              <ShieldAlert className="h-5 w-5 text-red-400" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Block Rate</p>
              <p className="text-2xl font-bold text-red-400">{overview.block_rate}%</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 bg-card/50 lg:col-span-2">
          <CardHeader>
            <CardTitle>Request Volume (7 days)</CardTitle>
          </CardHeader>
          <CardContent>
            {overview.daily_trend.length === 0 ? (
              <p className="py-16 text-center text-sm text-muted-foreground">No request volume recorded</p>
            ) : (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={overview.daily_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="total"
                  stroke="#6366f1"
                  fill="#6366f1"
                  fillOpacity={0.15}
                  name="Total"
                />
                <Area
                  type="monotone"
                  dataKey="blocked"
                  stroke="#ef4444"
                  fill="#ef4444"
                  fillOpacity={0.2}
                  name="Blocked"
                />
              </AreaChart>
            </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle>By Action</CardTitle>
          </CardHeader>
          <CardContent>
            {overview.by_action.length === 0 ? (
              <p className="py-16 text-center text-sm text-muted-foreground">No action breakdown available</p>
            ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={overview.by_action} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis type="number" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="action"
                  width={100}
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/50">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Distributed Traces</CardTitle>
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
                  <div className="mb-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>Actor: {trace.actor}</span>
                    <span>Risk: {trace.risk}</span>
                    <span>{trace.timestamp}</span>
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
    </div>
  );
}
