"use client";

import { useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FrameworkComplianceCard } from "@/components/compliance/framework-compliance-card";
import { ComplianceEvidencePanel } from "@/components/compliance/compliance-evidence-panel";
import { useComplianceFrameworks } from "@/hooks/use-compliance-frameworks";
import type { ApiDashboardOverview } from "@/lib/api";

type Framework = ApiDashboardOverview["compliance_frameworks"][number];

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
  const { data: frameworksData = [], isLoading, isError, refetch, isFetching } = useComplianceFrameworks();
  const [frameworkOverrides, setFrameworkOverrides] = useState<Record<string, Framework>>({});

  const frameworks = useMemo(() => {
    return frameworksData.map((framework) => frameworkOverrides[framework.name] ?? framework);
  }, [frameworksData, frameworkOverrides]);

  const avgScore =
    frameworks.length > 0
      ? Math.round(frameworks.reduce((sum, f) => sum + f.score, 0) / frameworks.length)
      : 0;

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading compliance posture…</p>;
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-border/60 bg-muted/10 px-6 py-12 text-center">
        <p className="text-sm text-muted-foreground">
          Could not load compliance frameworks. Refresh the page or try again later.
        </p>
        <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Re-evaluate frameworks after changes, then use manual fix or AI assist on each gap.
        </p>
        <Button variant="outline" size="sm" className="gap-2" disabled={isFetching} onClick={() => refetch()}>
          <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
          Refresh all
        </Button>
      </div>

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
          {frameworks.map((framework) => (
            <FrameworkComplianceCard
              key={framework.name}
              framework={framework}
              onFrameworkUpdated={(updated) =>
                setFrameworkOverrides((current) => ({ ...current, [updated.name]: updated }))
              }
            />
          ))}
        </div>
      )}

      <ComplianceEvidencePanel />
    </div>
  );
}
