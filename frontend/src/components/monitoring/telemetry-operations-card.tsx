"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Cpu, Gauge, ShieldAlert, Timer, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type ApiTelemetryOperations } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { useDateRangeStore } from "@/stores/date-range-store";

const EMPTY_OPS: ApiTelemetryOperations = {
  generated_at: "",
  requests_total: 0,
  requests_allowed: 0,
  requests_blocked: 0,
  requests_review: 0,
  tokens_total: 0,
  prompt_tokens: 0,
  completion_tokens: 0,
  p50_latency_ms: 0,
  p95_latency_ms: 0,
  block_rate: 0,
  by_action: [],
  by_status: [],
  recent_blocked: [],
};

const riskColors: Record<string, string> = {
  low: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  medium: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  critical: "bg-red-500/10 text-red-400 border-red-500/30",
};

/** S13-06 — Live operations panel consuming the /telemetry/operations facade. */
export function TelemetryOperationsCard() {
  const token = useAuthStore((s) => s.token);
  const from = useDateRangeStore((s) => s.from);
  const to = useDateRangeStore((s) => s.to);

  const { data, isLoading } = useQuery({
    queryKey: ["telemetry-operations", token, from, to],
    queryFn: () => api.getTelemetryOperations(token!, { from_date: from, to_date: to }),
    enabled: Boolean(token),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  const ops = data ?? EMPTY_OPS;

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          Live operations
        </CardTitle>
        <span className="text-xs text-muted-foreground">
          {isLoading ? "Loading…" : "Refreshing every 30s"}
        </span>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <OpsKpi
            icon={Zap}
            iconClass="text-indigo-400 bg-indigo-500/10"
            label="Requests"
            value={formatNumber(ops.requests_total)}
            sub={`${formatNumber(ops.requests_allowed)} allowed · ${formatNumber(ops.requests_blocked)} blocked`}
          />
          <OpsKpi
            icon={Cpu}
            iconClass="text-emerald-400 bg-emerald-500/10"
            label="Tokens"
            value={formatNumber(ops.tokens_total)}
            sub={`${formatNumber(ops.prompt_tokens)} prompt · ${formatNumber(ops.completion_tokens)} completion`}
          />
          <OpsKpi
            icon={Timer}
            iconClass="text-cyan-400 bg-cyan-500/10"
            label="P50 latency"
            value={`${ops.p50_latency_ms}ms`}
            sub="median"
          />
          <OpsKpi
            icon={Gauge}
            iconClass="text-amber-400 bg-amber-500/10"
            label="P95 latency"
            value={`${ops.p95_latency_ms}ms`}
            sub="worst-case"
          />
          <OpsKpi
            icon={ShieldAlert}
            iconClass="text-red-400 bg-red-500/10"
            label="Block rate"
            value={`${ops.block_rate}%`}
            sub={`${formatNumber(ops.requests_review)} under review`}
          />
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Recent blocked events
          </p>
          {ops.recent_blocked.length === 0 ? (
            <p className="rounded-lg border border-border/40 py-6 text-center text-sm text-muted-foreground">
              No blocked events in range
            </p>
          ) : (
            <ul className="divide-y divide-border/50 rounded-lg border border-border/40">
              {ops.recent_blocked.slice(0, 8).map((event) => (
                <li key={event.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                  <span className="w-28 shrink-0 font-mono text-xs text-muted-foreground">{event.timestamp}</span>
                  <Badge className={`shrink-0 border ${riskColors[event.risk] ?? riskColors.low}`}>
                    {event.risk}
                  </Badge>
                  <span className="min-w-0 flex-1 truncate">
                    <span className="font-medium">{event.action}</span>
                    <span className="ml-2 truncate text-xs text-muted-foreground">{event.resource}</span>
                  </span>
                  <span className="hidden max-w-[24rem] truncate text-xs text-muted-foreground sm:block">
                    {event.details}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function OpsKpi({
  icon: Icon,
  iconClass,
  label,
  value,
  sub,
}: {
  icon: typeof Activity;
  iconClass: string;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="rounded-lg border border-border/40 p-3">
      <div className="flex items-center gap-2">
        <div className={`rounded-md p-1.5 ${iconClass}`}>
          <Icon className="h-4 w-4" />
        </div>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
      <p className="mt-1 text-xl font-bold">{value}</p>
      <p className="truncate text-[11px] text-muted-foreground">{sub}</p>
    </div>
  );
}
