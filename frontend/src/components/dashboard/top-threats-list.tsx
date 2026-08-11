import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApiDashboardOverview } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import Link from "next/link";

export function TopThreatsList({ data }: { data: ApiDashboardOverview["top_threats"] }) {
  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle>Top Threats Detected</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No blocked threats in this period</p>
        ) : (
          <ul className="space-y-3">
            {data.map((threat, index) => (
              <li key={`${threat.name}-${index}`} className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-muted text-xs font-medium">
                    {index + 1}
                  </span>
                  <span className="truncate text-sm">{threat.name}</span>
                </div>
                <span className="shrink-0 text-sm font-semibold tabular-nums">{formatNumber(threat.count)}</span>
              </li>
            ))}
          </ul>
        )}
        <Link href="/audit-explorer" className="mt-4 inline-flex text-sm text-primary hover:underline">
          View audit log →
        </Link>
      </CardContent>
    </Card>
  );
}
