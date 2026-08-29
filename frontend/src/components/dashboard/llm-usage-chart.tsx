"use client";

import Link from "next/link";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Coins, Flame, Gauge, Route } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { ApiDashboardOverview } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

const COLORS = ["#3b82f6", "#8b5cf6", "#f97316", "#22c55e", "#6366f1", "#ec4899"];

type LlmUsageChartProps = {
  data: ApiDashboardOverview["llm_usage"];
  summary?: ApiDashboardOverview["llm_usage_summary"];
};

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatCompactTokens(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return formatNumber(value);
}

export function LlmUsageChart({ data, summary }: LlmUsageChartProps) {
  const chartData = data.map((entry, i) => ({ ...entry, color: COLORS[i % COLORS.length] }));

  const derivedSummary = summary ?? {
    total_tokens: chartData.reduce((sum, item) => sum + (item.total_tokens ?? 0), 0),
    token_utilization_pct: 0,
    avg_burn_usd_per_day: chartData.reduce((sum, item) => sum + (item.cost_usd ?? 0), 0) / 30,
    total_cost_usd: chartData.reduce((sum, item) => sum + (item.cost_usd ?? 0), 0),
    monthly_token_quota: 50_000_000,
  };

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 pb-3">
        <div>
          <CardTitle className="text-base">Top LLM Usage</CardTitle>
          <CardDescription>30-day routing share, token volume, and estimated spend.</CardDescription>
        </div>
        <Button variant="outline" size="sm" className="gap-1.5" asChild>
          <Link href="/llm-router">
            <Route className="h-3.5 w-3.5" />
            LLM Router
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No LLM providers registered</p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,220px)_1fr]">
            <div className="mx-auto w-full max-w-[220px]">
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={38}
                    outerRadius={58}
                    paddingAngle={2}
                    dataKey="percentage"
                    nameKey="model"
                  >
                    {chartData.map((entry) => (
                      <Cell key={entry.model} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value, _name, props) => [
                      `${value}% · ${formatNumber(props.payload.requests)} req · ${formatCompactTokens(props.payload.total_tokens ?? 0)} tok`,
                      props.payload.model,
                    ]}
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-1 space-y-1">
                {chartData.map((entry) => (
                  <div key={entry.model} className="flex items-center justify-between gap-2 text-xs">
                    <span className="flex min-w-0 items-center gap-1.5 truncate text-muted-foreground">
                      <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: entry.color }} />
                      {entry.model}
                    </span>
                    <span className="shrink-0 font-medium">{entry.percentage.toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <MetricTile
                  icon={Gauge}
                  label="Token utilization"
                  value={`${derivedSummary.token_utilization_pct.toFixed(1)}%`}
                  hint={`${formatCompactTokens(derivedSummary.total_tokens)} / ${formatCompactTokens(derivedSummary.monthly_token_quota)} quota`}
                />
                <MetricTile
                  icon={Flame}
                  label="Avg burn"
                  value={formatUsd(derivedSummary.avg_burn_usd_per_day)}
                  hint="Estimated daily spend (30d window)"
                />
                <MetricTile
                  icon={Coins}
                  label="Period cost"
                  value={formatUsd(derivedSummary.total_cost_usd)}
                  hint="Blended model pricing"
                />
                <MetricTile
                  icon={Route}
                  label="Total tokens"
                  value={formatCompactTokens(derivedSummary.total_tokens)}
                  hint={`~${formatNumber(Math.round(derivedSummary.total_tokens / Math.max(chartData.reduce((s, i) => s + i.requests, 0), 1)))} avg / request`}
                />
              </div>

              <div className="overflow-x-auto rounded-lg border border-border/60">
                <table className="w-full min-w-[340px] text-xs">
                  <thead>
                    <tr className="border-b border-border/60 text-left text-muted-foreground">
                      <th className="px-3 py-2 font-medium">Model</th>
                      <th className="px-3 py-2 font-medium text-right">Requests</th>
                      <th className="px-3 py-2 font-medium text-right hidden sm:table-cell">Tokens</th>
                      <th className="px-3 py-2 font-medium text-right hidden md:table-cell">Avg tok/req</th>
                      <th className="px-3 py-2 font-medium text-right">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {chartData.map((entry) => (
                      <tr key={entry.model} className="border-b border-border/40 last:border-0">
                        <td className="px-3 py-2 font-medium">{entry.model}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{formatNumber(entry.requests)}</td>
                        <td className="px-3 py-2 text-right tabular-nums hidden sm:table-cell">
                          {formatCompactTokens(entry.total_tokens ?? 0)}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums hidden md:table-cell">
                          {formatNumber(Math.round(entry.avg_tokens_per_request ?? 0))}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">{formatUsd(entry.cost_usd ?? 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MetricTile({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: typeof Gauge;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-muted/10 px-3 py-2.5">
      <div className="mb-1 flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className="text-lg font-semibold tabular-nums">{value}</p>
      <p className="mt-0.5 text-[10px] text-muted-foreground">{hint}</p>
    </div>
  );
}
