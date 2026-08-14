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
import { MetricCard, MetricStrip } from "@/components/dashboard/metric-card";
import { MetricInsightModal } from "@/components/dashboard/metric-insight-modal";
import { TelemetryOperationsCard } from "@/components/monitoring/telemetry-operations-card";
import { GatewaySlaCard } from "@/components/monitoring/gateway-sla-card";
import { SectionHeading, SectionTabBar } from "@/components/shared/section-chrome";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useMetricInsight } from "@/hooks/use-metric-insight";
import { useObservability } from "@/hooks/use-observability";
import { resolveMetricInsightKey } from "@/lib/dashboard-metric-insights";

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

type DetailTab = "breakdown" | "operations";

const DETAIL_TABS: { id: DetailTab; label: string }[] = [
  { id: "breakdown", label: "Action breakdown" },
  { id: "operations", label: "Ops & SLA" },
];

export function MonitoringOverviewTab() {
  const { overview: overviewData, isLoading, isError } = useObservability();
  const overview = overviewData ?? EMPTY_OVERVIEW;
  const [detailTab, setDetailTab] = useState<DetailTab>("breakdown");
  const {
    openMetricInsight,
    closeMetricInsight,
    insightOpen,
    activeContext,
    insightLoading,
    insight,
    insightError,
  } = useMetricInsight();

  if (isLoading && !overviewData) {
    return <p className="text-sm text-muted-foreground">Loading overview…</p>;
  }

  if (isError && !overviewData) {
    return (
      <p className="rounded-lg border border-border/60 bg-muted/10 px-6 py-8 text-center text-sm text-muted-foreground">
        Could not load monitoring overview.
      </p>
    );
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="space-y-8">
      <section className="space-y-3">
        <SectionHeading title="At a glance" />
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            variant="hero"
            showTrend={false}
            title="Events (range)"
            value={overview.total_events_today}
            change={0}
            periodLabel="selected range"
            icon={Activity}
            iconColor="text-indigo-400"
            insightKey={resolveMetricInsightKey("Events (range)")}
            onInsightClick={openMetricInsight}
          />
          <MetricCard
            variant="hero"
            showTrend={false}
            title="Avg latency"
            value={`${overview.avg_latency_ms}ms`}
            change={0}
            icon={Zap}
            iconColor="text-emerald-400"
          />
          <MetricCard
            variant="hero"
            showTrend={false}
            title="P95 latency"
            value={`${overview.p95_latency_ms}ms`}
            change={0}
            icon={Clock}
            iconColor="text-amber-400"
          />
          <MetricCard
            variant="hero"
            showTrend={false}
            title="Block rate"
            value={`${overview.block_rate}%`}
            change={0}
            periodLabel="selected range"
            format="raw"
            icon={ShieldAlert}
            iconColor="text-red-400"
            insightKey={resolveMetricInsightKey("Block rate")}
            onInsightClick={openMetricInsight}
          />
        </div>
      </section>

      <section className="space-y-3">
        <SectionHeading title="Request outcomes" />
        <MetricStrip
          onInsightClick={openMetricInsight}
          items={[
            {
              title: "Allowed",
              value: overview.allowed_today,
              change: 0,
              periodLabel: "selected range",
              icon: Activity,
              iconColor: "text-emerald-400",
              showTrend: false,
              insightKey: resolveMetricInsightKey("Allowed"),
            },
            {
              title: "Blocked",
              value: overview.blocked_today,
              change: 0,
              periodLabel: "selected range",
              icon: ShieldAlert,
              iconColor: "text-red-400",
              showTrend: false,
              insightKey: resolveMetricInsightKey("Blocked"),
            },
            {
              title: "Under review",
              value: overview.under_review_today,
              change: 0,
              icon: Clock,
              iconColor: "text-amber-400",
              showTrend: false,
            },
          ]}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-12">
        <Card className="border-border/60 bg-card/50 lg:col-span-8">
          <CardHeader>
            <CardTitle className="text-base">Request volume (7 days)</CardTitle>
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

        <Card className="border-border/60 bg-card/50 lg:col-span-4">
          <CardHeader>
            <CardTitle className="text-base">By risk</CardTitle>
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
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Operational detail</h2>
          <SectionTabBar tabs={DETAIL_TABS} active={detailTab} onChange={setDetailTab} />
        </div>

        {detailTab === "breakdown" && (
          <Card className="border-border/60 bg-card/50">
            <CardHeader>
              <CardTitle className="text-base">By action</CardTitle>
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
        )}

        {detailTab === "operations" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <TelemetryOperationsCard />
            <GatewaySlaCard />
          </div>
        )}
      </section>

      <MetricInsightModal
        open={insightOpen}
        loading={insightLoading}
        insight={insight}
        error={insightError}
        pendingTitle={activeContext?.cardTitle}
        onClose={closeMetricInsight}
      />
    </div>
    </TooltipProvider>
  );
}
