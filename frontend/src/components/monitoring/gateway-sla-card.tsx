"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Gauge, Layers3, Timer } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type ApiGatewaySla } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useDateRangeStore } from "@/stores/date-range-store";

const EMPTY_SLA: ApiGatewaySla = {
  generated_at: "",
  period_days: 7,
  requests_total: 0,
  successful_requests: 0,
  failed_requests: 0,
  availability_percent: 100,
  error_rate_percent: 0,
  p50_latency_ms: 0,
  p95_latency_ms: 0,
  p99_latency_ms: 0,
  average_gateway_overhead_ms: 0,
  providers_active: 0,
  pooling_instrumented: false,
  pool_reuse_rate_percent: null,
  pool_note: "",
};

export function GatewaySlaCard() {
  const token = useAuthStore((s) => s.token);
  const from = useDateRangeStore((s) => s.from);
  const to = useDateRangeStore((s) => s.to);
  const { data, isLoading } = useQuery({
    queryKey: ["telemetry-sla", token, from, to],
    queryFn: () => api.getTelemetrySla(token!, { from_date: from, to_date: to }),
    enabled: Boolean(token),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
  const sla = data ?? EMPTY_SLA;
  const healthy = sla.error_rate_percent < 1 && sla.availability_percent >= 99;

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Gauge className="h-4 w-4 text-cyan-400" />
          Gateway SLA
        </CardTitle>
        <Badge className={healthy ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" : "border-amber-500/30 bg-amber-500/10 text-amber-400"}>
          {isLoading ? "Loading" : healthy ? "Healthy" : "Review"}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SlaMetric icon={Activity} label="Availability" value={`${sla.availability_percent}%`} sub={`${sla.failed_requests} failed requests`} />
          <SlaMetric icon={Timer} label="P99 latency" value={`${sla.p99_latency_ms}ms`} sub={`P95 ${sla.p95_latency_ms}ms`} />
          <SlaMetric icon={Layers3} label="Gateway overhead" value={`${sla.average_gateway_overhead_ms}ms`} sub={`${sla.providers_active} active providers`} />
          <SlaMetric icon={Gauge} label="Error rate" value={`${sla.error_rate_percent}%`} sub={`${sla.requests_total} requests`} />
        </div>
        <div className="flex items-start gap-2 rounded-lg border border-border/40 px-3 py-2 text-xs text-muted-foreground">
          <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${sla.pooling_instrumented ? "bg-emerald-400" : "bg-amber-400"}`} />
          <span>{sla.pooling_instrumented ? `Pool reuse ${sla.pool_reuse_rate_percent ?? 0}%` : sla.pool_note}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function SlaMetric({ icon: Icon, label, value, sub }: { icon: typeof Activity; label: string; value: string; sub: string }) {
  return (
    <div className="rounded-lg border border-border/40 p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="h-4 w-4 text-cyan-400" />
        {label}
      </div>
      <p className="mt-1 text-xl font-bold">{value}</p>
      <p className="truncate text-[11px] text-muted-foreground">{sub}</p>
    </div>
  );
}