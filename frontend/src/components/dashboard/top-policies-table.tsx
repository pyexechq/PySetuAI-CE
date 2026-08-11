import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApiDashboardOverview } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

export function TopPoliciesTable({ data }: { data: ApiDashboardOverview["top_policies"] }) {
  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle>Top Policies</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No policies configured</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">#</th>
                <th className="pb-2 font-medium">Policy</th>
                <th className="pb-2 text-right font-medium">Requests</th>
                <th className="pb-2 text-right font-medium">Violations</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.name} className="border-b border-border/50 last:border-0">
                  <td className="py-2 text-muted-foreground">{row.rank}</td>
                  <td className="py-2">{row.name}</td>
                  <td className="py-2 text-right">{formatNumber(row.requests)}</td>
                  <td className="py-2 text-right text-red-400">{formatNumber(row.violations)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}
