import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ApiDashboardOverview } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

export function McpActivityTable({ data }: { data: ApiDashboardOverview["mcp_activity"] }) {
  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle>MCP Server Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No MCP servers registered</p>
        ) : (
          <div className="overflow-x-auto">
<table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-3 font-medium">Server</th>
                <th className="pb-3 text-right font-medium">Total Calls</th>
                <th className="pb-3 text-right font-medium">Blocked</th>
                <th className="pb-3 font-medium">Risk</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.server} className="border-b border-border/50 last:border-0">
                  <td className="py-3">{row.server}</td>
                  <td className="py-3 text-right">{formatNumber(row.total_calls)}</td>
                  <td className="py-3 text-right text-red-400">{formatNumber(row.blocked)}</td>
                  <td className="py-3">
                    <Badge variant={row.risk === "High" ? "destructive" : row.risk === "Medium" ? "warning" : "success"}>
                      {row.risk}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
