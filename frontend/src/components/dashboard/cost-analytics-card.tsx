"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, Coins, Loader2, Users } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiCostAnalytics } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { formatNumber } from "@/lib/utils";

const tabs = [
  { id: "model", label: "Models" },
  { id: "user", label: "Users" },
  { id: "team", label: "API keys / teams" },
] as const;

type TabId = (typeof tabs)[number]["id"];

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function CostAnalyticsCard() {
  const token = useAuthStore((s) => s.token);
  const [tab, setTab] = useState<TabId>("model");
  const { data, isLoading } = useQuery({
    queryKey: ["cost-analytics", token],
    queryFn: () => api.getCostAnalytics(token!),
    enabled: Boolean(token),
  });

  if (isLoading || !data) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading cost analytics…
        </CardContent>
      </Card>
    );
  }

  const rows =
    tab === "model" ? data.by_model : tab === "user" ? data.by_user : data.by_team;

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 pb-3">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="h-4 w-4 text-sky-400" />
            Cost & token analytics
          </CardTitle>
          <CardDescription>
            Live attribution from gateway <code className="text-xs">usage_metadata</code> — last {data.period_days} days.
          </CardDescription>
        </div>
        <Badge variant="outline" className="gap-1">
          <Coins className="h-3 w-3" />
          {formatUsd(data.summary.total_cost_usd)}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-border/60 p-3">
            <p className="text-xs text-muted-foreground">Requests</p>
            <p className="text-xl font-semibold tabular-nums">{formatNumber(data.summary.requests)}</p>
          </div>
          <div className="rounded-md border border-border/60 p-3">
            <p className="text-xs text-muted-foreground">Tokens</p>
            <p className="text-xl font-semibold tabular-nums">{formatNumber(data.summary.total_tokens)}</p>
          </div>
          <div className="rounded-md border border-border/60 p-3">
            <p className="text-xs text-muted-foreground">Avg $ / request</p>
            <p className="text-xl font-semibold tabular-nums">{formatUsd(data.summary.avg_cost_per_request_usd)}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {tabs.map((item) => (
            <Button
              key={item.id}
              size="sm"
              variant={tab === item.id ? "default" : "outline"}
              onClick={() => setTab(item.id)}
            >
              {item.id === "user" && <Users className="mr-1.5 h-3.5 w-3.5" />}
              {item.label}
            </Button>
          ))}
        </div>

        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No attributed LLM traffic in this period yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-md border border-border/60">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2 text-right">Requests</th>
                  <th className="px-3 py-2 text-right">Tokens</th>
                  <th className="px-3 py-2 text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 12).map((row) => (
                  <tr key={row.key} className="border-t border-border/40">
                    <td className="px-3 py-2 font-medium">{row.label}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{formatNumber(row.requests)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{formatNumber(row.total_tokens)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{formatUsd(row.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data.daily_trend.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Daily burn (recent)</p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {data.daily_trend.slice(-4).map((point) => (
                <div key={point.date} className="rounded-md border border-border/60 px-3 py-2 text-xs">
                  <p className="text-muted-foreground">{point.date}</p>
                  <p className="font-medium tabular-nums">{formatUsd(point.cost_usd)}</p>
                  <p className="text-muted-foreground">{formatNumber(point.total_tokens)} tokens</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
