"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface UagRouteItem {
  route: string;
  count: number;
}

interface UagTranslationChartProps {
  routes: UagRouteItem[];
}

export function UagTranslationChart({ routes }: UagTranslationChartProps) {
  const maxCount = Math.max(...routes.map((route) => route.count), 1);

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="text-base">Protocol translation routes</CardTitle>
        <CardDescription>Top source → target provider paths in the last 30 days.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {routes.length === 0 ? (
          <p className="text-sm text-muted-foreground">No translation events yet.</p>
        ) : (
          routes.map((route) => (
            <div key={route.route} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span>{route.route}</span>
                <span className="text-muted-foreground">{route.count.toLocaleString()}</span>
              </div>
              <div className="h-2 rounded-full bg-muted/40">
                <div
                  className="h-2 rounded-full bg-primary/70"
                  style={{ width: `${Math.max(8, (route.count / maxCount) * 100)}%` }}
                />
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
