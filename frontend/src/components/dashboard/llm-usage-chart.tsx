"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApiDashboardOverview } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

const COLORS = ["#3b82f6", "#8b5cf6", "#f97316", "#22c55e", "#6366f1", "#ec4899"];

export function LlmUsageChart({ data }: { data: ApiDashboardOverview["llm_usage"] }) {
  const chartData = data.map((entry, i) => ({ ...entry, color: COLORS[i % COLORS.length] }));

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle>Top LLM Usage</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">No LLM providers registered</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="percentage"
                nameKey="model"
                label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {chartData.map((entry) => (
                  <Cell key={entry.model} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value, _name, props) => [
                  `${value}% (${formatNumber(props.payload.requests)} requests)`,
                  props.payload.model,
                ]}
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
