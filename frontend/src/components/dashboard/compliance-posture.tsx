import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ApiDashboardOverview } from "@/lib/api";
import { cn } from "@/lib/utils";

const statusLabel = {
  compliant: { label: "Compliant", variant: "success" as const },
  partial: { label: "Partial", variant: "warning" as const },
  "at-risk": { label: "At Risk", variant: "destructive" as const },
};

export function CompliancePosture({ data }: { data: ApiDashboardOverview["compliance_frameworks"] }) {
  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle>Compliance Posture</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {data.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No compliance data available</p>
        ) : (
          data.map((fw) => {
            const status = statusLabel[fw.status as keyof typeof statusLabel] ?? statusLabel.partial;
            return (
              <div key={fw.name} className="flex items-center justify-between rounded-md border border-border/60 p-3">
                <div>
                  <p className="font-medium">{fw.name}</p>
                  <p className={cn("text-xs text-muted-foreground", fw.status === "at-risk" && "text-red-400")}>
                    {fw.passed}/{fw.controls} controls
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold">{Math.round(fw.score)}%</span>
                  <Badge variant={status.variant}>{status.label}</Badge>
                </div>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
