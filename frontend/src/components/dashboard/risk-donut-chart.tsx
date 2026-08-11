"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApiDashboardOverview } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

const RISK_COLORS: Record<string, string> = {
  Low: "#22c55e",
  Medium: "#eab308",
  High: "#f97316",
  Critical: "#ef4444",
};

export function RiskDonutChart({ data }: { data: ApiDashboardOverview["risk_distribution"] }) {
  const chartData = data.map((item) => ({
    ...item,
    color: RISK_COLORS[item.level] ?? "#6366f1",
  }));
  const total = chartData.reduce((sum, item) => sum + item.count, 0);

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle>Request Risk Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="py-16 text-center text-sm text-muted-foreground">No risk events in this period</p>
        ) : (
          <>
            <div className="relative">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={chartData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={2} dataKey="count">
                    {chartData.map((entry) => (
                      <Cell key={entry.level} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold">{formatNumber(total)}</span>
                <span className="text-xs text-muted-foreground">Total</span>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {chartData.map((item) => (
                <div key={item.level} className="flex items-center gap-2 text-sm">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-muted-foreground">{item.level}</span>
                  <span className="ml-auto font-medium">{item.percentage}%</span>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
