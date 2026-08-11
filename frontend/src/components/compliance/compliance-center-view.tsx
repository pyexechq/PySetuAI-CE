"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FrameworkControlPanel } from "@/components/compliance/framework-control-panel";
import { ComplianceEvidencePanel } from "@/components/compliance/compliance-evidence-panel";
import { EMPTY_DASHBOARD_OVERVIEW, useDashboardOverview } from "@/hooks/use-dashboard-overview";
import { cn } from "@/lib/utils";

const statusLabel = {
  compliant: { label: "Compliant", variant: "success" as const },
  partial: { label: "Partial", variant: "warning" as const },
  "at-risk": { label: "At Risk", variant: "destructive" as const },
};

function CircularProgress({ score, size = 80 }: { score: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 90 ? "#22c55e" : score >= 80 ? "#eab308" : "#ef4444";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="hsl(var(--muted))" strokeWidth="6" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-lg font-bold">{Math.round(score)}%</span>
      </div>
    </div>
  );
}

export function ComplianceCenterView() {
  const { data: overview, isLoading } = useDashboardOverview();
  const frameworks = overview?.compliance_frameworks ?? EMPTY_DASHBOARD_OVERVIEW.compliance_frameworks;
  const avgScore =
    frameworks.length > 0
      ? Math.round(frameworks.reduce((sum, f) => sum + f.score, 0) / frameworks.length)
      : 0;

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading compliance posture…</p>;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="border-border/60 bg-card/50">
          <CardContent className="flex items-center gap-4 p-5">
            <CircularProgress score={avgScore} />
            <div>
              <p className="text-sm text-muted-foreground">Overall Score</p>
              <p className="text-xl font-bold">{avgScore}%</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Frameworks Tracked</p>
            <p className="text-2xl font-bold">{frameworks.length}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Compliant</p>
            <p className="text-2xl font-bold text-emerald-400">
              {frameworks.filter((f) => f.status === "compliant").length}
            </p>
          </CardContent>
        </Card>
      </div>

      {frameworks.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">No compliance data available yet</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {frameworks.map((framework) => {
            const status = statusLabel[framework.status as keyof typeof statusLabel] ?? statusLabel.partial;
            const inProgress = framework.in_progress ?? 0;
            const notMet = framework.not_met ?? Math.max(0, framework.controls - framework.passed - inProgress);
            const controlItems = framework.control_items ?? [];

            return (
              <Card key={framework.name} className="border-border/60 bg-card/50">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold">{framework.name}</h3>
                      <Badge variant={status.variant} className="mt-2">
                        {status.label}
                      </Badge>
                    </div>
                    <CircularProgress score={framework.score} size={64} />
                  </div>
                  <div className="mt-4 flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Key controls</span>
                    <span>
                      <span className={cn(framework.passed === framework.controls ? "text-emerald-400" : "")}>
                        {framework.passed}
                      </span>
                      /{framework.controls} met
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${framework.controls ? (framework.passed / framework.controls) * 100 : 0}%` }}
                    />
                  </div>

                  {controlItems.length > 0 && (
                    <FrameworkControlPanel
                      controls={controlItems}
                      passed={framework.passed}
                      inProgress={inProgress}
                      notMet={notMet}
                    />
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <ComplianceEvidencePanel />
    </div>
  );
}
