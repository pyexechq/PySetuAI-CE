"use client";

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
import { TelemetryOperationsCard } from "@/components/monitoring/telemetry-operations-card";
import { GatewaySlaCard } from "@/components/monitoring/gateway-sla-card";
import { useObservability } from "@/hooks/use-observability";
import { formatNumber } from "@/lib/utils";

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

export function MonitoringOverviewTab() {
  const { overview: overviewData, isLoading } = useObservability();
  const overview = overviewData ?? EMPTY_OVERVIEW;

  if (isLoading && !overviewData) {
    return <p className="text-sm text-muted-foreground">Loading overview…</p>;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          icon={Activity}
          iconClass="text-indigo-400 bg-indigo-500/10"
          label="Events (range)"
          value={formatNumber(overview.total_events_today)}
        />
        <KpiCard
          icon={Zap}
          iconClass="text-emerald-400 bg-emerald-500/10"
          label="Avg latency"
          value={`${overview.avg_latency_ms}ms`}
        />
        <KpiCard
          icon={Clock}
          iconClass="text-amber-400 bg-amber-500/10"
          label="P95 latency"
          value={`${overview.p95_latency_ms}ms`}
        />
        <KpiCard
          icon={ShieldAlert}
          iconClass="text-red-400 bg-red-500/10"
          label="Block rate"
          value={`${overview.block_rate}%`}
          valueClass="text-red-400"
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatusChip label="Allowed" value={overview.allowed_today} variant="success" />
        <StatusChip label="Blocked" value={overview.blocked_today} variant="destructive" />
        <StatusChip label="Under review" value={overview.under_review_today} variant="warning" />
      </div>

      <TelemetryOperationsCard />

      <GatewaySlaCard />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 bg-card/50 lg:col-span-2">
          <CardHeader>
            <CardTitle>Request volume (7 days)</CardTitle>
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
            <CardTitle>By risk</CardTitle>
          </CardHeader>
          <CardContent>
            {overview.by_risk.length === 0 ? (
              <p className="py-16 text-center text-sm text-muted-foreground">No risk breakdown</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={overview.by_risk} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis type="number" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                  <YAxis
                    type="category"
                    dataKey="risk"
                    width={72}
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="count" fill="#f97316" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle>By action</CardTitle>
        </CardHeader>
        <CardContent>
          {overview.by_action.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No action breakdown available</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={overview.by_action}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="action" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function KpiCard({
  icon: Icon,
  iconClass,
  label,
  value,
  valueClass,
}: {
  icon: typeof Activity;
  iconClass: string;
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <Card className="border-border/60 bg-card/50">
      <CardContent className="flex items-center gap-3 p-5">
        <div className={`rounded-lg p-2 ${iconClass}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className={`text-2xl font-bold ${valueClass ?? ""}`}>{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function StatusChip({
  label,
  value,
  variant,
}: {
  label: string;
  value: number;
  variant: "success" | "destructive" | "warning";
}) {
  const colors = {
    success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    destructive: "border-red-500/30 bg-red-500/10 text-red-400",
    warning: "border-amber-500/30 bg-amber-500/10 text-amber-400",
  };
  return (
    <div className={`rounded-lg border px-4 py-3 ${colors[variant]}`}>
      <p className="text-xs uppercase tracking-wide opacity-80">{label}</p>
      <p className="text-xl font-semibold">{formatNumber(value)}</p>
    </div>
  );
}
