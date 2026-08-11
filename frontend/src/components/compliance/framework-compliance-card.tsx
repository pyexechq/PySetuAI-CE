"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ClipboardList,
  Download,
  Loader2,
  RefreshCw,
  Sparkles,
  Wrench,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FrameworkControlPanel } from "@/components/compliance/framework-control-panel";
import { ComplianceRemediationDialog } from "@/components/compliance/compliance-remediation-dialog";
import { useComplianceActions } from "@/hooks/use-compliance-actions";
import type { ApiComplianceControl, ApiComplianceRemediationResponse, ApiDashboardOverview } from "@/lib/api";
import { complianceFrameworkSlug } from "@/lib/compliance-routes";
import { cn } from "@/lib/utils";

type Framework = ApiDashboardOverview["compliance_frameworks"][number];

const statusLabel = {
  compliant: { label: "Compliant", variant: "success" as const },
  partial: { label: "Partial", variant: "warning" as const },
  "at-risk": { label: "At Risk", variant: "destructive" as const },
};

function CircularProgress({ score, size = 64 }: { score: number; size?: number }) {
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
        <span className="text-sm font-bold">{Math.round(score)}%</span>
      </div>
    </div>
  );
}

function exportFrameworkCsv(framework: Framework) {
  const rows = [
    ["Framework", "Control ID", "Title", "Status", "Requirement", "Evidence", "Remediation", "Module"],
    ...(framework.control_items ?? []).map((control) => [
      framework.name,
      control.id,
      control.title,
      control.status,
      control.requirement,
      control.evidence ?? "",
      control.remediation ?? "",
      control.pysetu_module ?? "",
    ]),
  ];
  const csv = rows.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${complianceFrameworkSlug(framework.name)}-controls.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

interface FrameworkComplianceCardProps {
  framework: Framework;
  onFrameworkUpdated: (framework: Framework) => void;
}

export function FrameworkComplianceCard({ framework, onFrameworkUpdated }: FrameworkComplianceCardProps) {
  const { reevaluateFramework, generateRemediation } = useComplianceActions();
  const [localFramework, setLocalFramework] = useState(framework);
  const [lastEvaluated, setLastEvaluated] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogLoading, setDialogLoading] = useState(false);
  const [plan, setPlan] = useState<ApiComplianceRemediationResponse | null>(null);
  const [activeControlTitle, setActiveControlTitle] = useState<string | undefined>();

  const status = statusLabel[localFramework.status as keyof typeof statusLabel] ?? statusLabel.partial;
  const inProgress = localFramework.in_progress ?? 0;
  const notMet = localFramework.not_met ?? Math.max(0, localFramework.controls - localFramework.passed - inProgress);
  const controlItems = localFramework.control_items ?? [];
  const slug = complianceFrameworkSlug(localFramework.name);
  const gapCount = notMet + inProgress;

  async function handleReevaluate() {
    const result = await reevaluateFramework.mutateAsync(slug);
    setLocalFramework(result.framework);
    setLastEvaluated(new Date(result.evaluated_at).toLocaleString());
    onFrameworkUpdated(result.framework);
  }

  async function handleRemediation(control: ApiComplianceControl, mode: "manual" | "ai") {
    setActiveControlTitle(control.title);
    setDialogOpen(true);
    setDialogLoading(true);
    setPlan(null);
    try {
      const result = await generateRemediation.mutateAsync({
        framework_name: localFramework.name,
        control_id: control.id,
        mode,
      });
      setPlan(result);
    } finally {
      setDialogLoading(false);
    }
  }

  return (
    <>
      <Card className="border-border/60 bg-card/50">
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold">{localFramework.name}</h3>
              <Badge variant={status.variant} className="mt-2">
                {status.label}
              </Badge>
              {lastEvaluated && (
                <p className="mt-2 text-[10px] text-muted-foreground">Re-evaluated {lastEvaluated}</p>
              )}
            </div>
            <CircularProgress score={localFramework.score} />
          </div>

          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Key controls</span>
            <span>
              <span className={cn(localFramework.passed === localFramework.controls ? "text-emerald-400" : "")}>
                {localFramework.passed}
              </span>
              /{localFramework.controls} met
            </span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{
                width: `${localFramework.controls ? (localFramework.passed / localFramework.controls) * 100 : 0}%`,
              }}
            />
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1 text-xs"
              disabled={reevaluateFramework.isPending}
              onClick={() => void handleReevaluate()}
            >
              {reevaluateFramework.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              Re-evaluate
            </Button>
            <Button size="sm" variant="outline" className="h-8 gap-1 text-xs" onClick={() => exportFrameworkCsv(localFramework)}>
              <Download className="h-3.5 w-3.5" />
              Export CSV
            </Button>
            {gapCount > 0 && (
              <Button size="sm" variant="secondary" className="h-8 gap-1 text-xs" asChild>
                <Link href="/reports">
                  <ClipboardList className="h-3.5 w-3.5" />
                  {gapCount} gap{gapCount === 1 ? "" : "s"}
                </Link>
              </Button>
            )}
          </div>

          {controlItems.length > 0 && (
            <FrameworkControlPanel
              controls={controlItems}
              passed={localFramework.passed}
              inProgress={inProgress}
              notMet={notMet}
              onManualFix={(control) => void handleRemediation(control, "manual")}
              onAiAssist={(control) => void handleRemediation(control, "ai")}
              remediationLoading={generateRemediation.isPending}
            />
          )}
        </CardContent>
      </Card>

      <ComplianceRemediationDialog
        open={dialogOpen}
        loading={dialogLoading}
        plan={plan}
        controlTitle={activeControlTitle}
        onClose={() => setDialogOpen(false)}
      />
    </>
  );
}
