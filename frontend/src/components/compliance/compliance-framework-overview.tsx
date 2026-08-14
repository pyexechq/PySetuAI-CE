"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ApiDashboardOverview } from "@/lib/api";
import { cn } from "@/lib/utils";

type Framework = ApiDashboardOverview["compliance_frameworks"][number];

const DONUT_COLORS = ["#22c55e", "#eab308", "#ef4444"];

function scoreColor(score: number) {
  if (score >= 90) return "bg-emerald-500";
  if (score >= 80) return "bg-amber-500";
  return "bg-red-500";
}

export function ComplianceFrameworkOverview({ frameworks }: { frameworks: Framework[] }) {
  const statusCounts = {
    compliant: frameworks.filter((f) => f.status === "compliant").length,
    partial: frameworks.filter((f) => f.status === "partial").length,
    atRisk: frameworks.filter((f) => f.status === "at-risk").length,
  };

  const donutData = [
    { name: "Compliant", value: statusCounts.compliant },
    { name: "Partial", value: statusCounts.partial },
    { name: "At risk", value: statusCounts.atRisk },
  ].filter((item) => item.value > 0);

  return (
    <div className="grid gap-4 lg:grid-cols-12">
      <Card className="border-border/60 bg-card/50 lg:col-span-4">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Framework posture</CardTitle>
        </CardHeader>
        <CardContent>
          {donutData.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No framework data</p>
          ) : (
            <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:justify-center">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie data={donutData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={48} outerRadius={72}>
                    {donutData.map((entry, index) => (
                      <Cell key={entry.name} fill={DONUT_COLORS[index % DONUT_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2 text-sm">
                {donutData.map((item, index) => (
                  <div key={item.name} className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: DONUT_COLORS[index % DONUT_COLORS.length] }}
                    />
                    <span className="text-muted-foreground">{item.name}</span>
                    <span className="font-medium tabular-nums">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card/50 lg:col-span-8">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Score by framework</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {frameworks.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No frameworks tracked</p>
          ) : (
            frameworks.map((framework) => (
                <div key={framework.name} className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2 text-sm">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="truncate font-medium">{framework.name}</span>
                      <Badge
                        variant={
                          framework.status === "compliant"
                            ? "success"
                            : framework.status === "partial"
                              ? "warning"
                              : "destructive"
                        }
                        className="shrink-0 text-[10px]"
                      >
                        {framework.status === "at-risk" ? "At risk" : framework.status}
                      </Badge>
                    </div>
                    <span className="shrink-0 tabular-nums text-muted-foreground">
                      {framework.passed} met
                      {(framework.in_progress ?? 0) > 0 ? ` · ${framework.in_progress} in progress` : ""}
                      {(framework.not_met ?? 0) > 0 ? ` · ${framework.not_met} gaps` : ""}
                      {" · "}
                      {Math.round(framework.score)}%
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn("h-full rounded-full transition-all", scoreColor(framework.score))}
                      style={{ width: `${Math.max(0, Math.min(100, framework.score))}%` }}
                    />
                  </div>
                </div>
              ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
