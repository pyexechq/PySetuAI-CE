"use client";

import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataResidencyMap } from "@/components/data-protection/data-residency-map";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { formatNumber } from "@/lib/utils";

export function DataProtectionView() {
  const token = useAuthStore((s) => s.token);
  const { data, isLoading } = useQuery({
    queryKey: ["data-protection-overview", token],
    queryFn: () => api.getDataProtectionOverview(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const dataClassifications = data?.classifications ?? [];
  const regions = data?.regions ?? [];
  const total = dataClassifications.reduce((sum, d) => sum + d.count, 0);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle>Classification Inventory</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="py-16 text-center text-sm text-muted-foreground">Loading classification data…</p>
          ) : dataClassifications.length === 0 ? (
            <p className="py-16 text-center text-sm text-muted-foreground">No classified events in this period</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={dataClassifications}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={110}
                    paddingAngle={3}
                  >
                    {dataClassifications.map((entry) => (
                      <Cell key={entry.label} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                    formatter={(value) => formatNumber(Number(value))}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-4 grid grid-cols-2 gap-3">
                {dataClassifications.map((item) => (
                  <div key={item.label} className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                    <div>
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatNumber(item.count)} ({item.percentage}%)
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle>Data Residency Map</CardTitle>
        </CardHeader>
        <CardContent>
          <DataResidencyMap regions={regions} />
          <p className="mt-3 text-center text-sm text-muted-foreground">
            Total scanned events: {formatNumber(data?.total_scanned ?? total)} · PII redactions:{" "}
            {formatNumber(data?.pii_redactions ?? 0)}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
