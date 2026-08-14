"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ClipboardList,
  Download,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { FrameworkControlPanel } from "@/components/compliance/framework-control-panel";
import { ComplianceRemediationDialog } from "@/components/compliance/compliance-remediation-dialog";
import { useComplianceActions } from "@/hooks/use-compliance-actions";
import type { ApiComplianceControl, ApiComplianceRemediationResponse, ApiDashboardOverview } from "@/lib/api";
import { complianceFrameworkSlug } from "@/lib/compliance-routes";
import { usePreferencesStore } from "@/stores/preferences-store";
import { formatDateTime } from "@/lib/date-utils";
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
  const timezone = usePreferencesStore((s) => s.timezone);
  const [localFramework, setLocalFramework] = useState(framework);
  const [evaluatedAt, setEvaluatedAt] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogLoading, setDialogLoading] = useState(false);
  const [plan, setPlan] = useState<ApiComplianceRemediationResponse | null>(null);
  const [activeControlTitle, setActiveControlTitle] = useState<string | undefined>();

  useEffect(() => {
    setLocalFramework(framework);
  }, [framework]);

  const status = statusLabel[localFramework.status as keyof typeof statusLabel] ?? statusLabel.partial;
  const inProgress = localFramework.in_progress ?? 0;
  const notMet = localFramework.not_met ?? Math.max(0, localFramework.controls - localFramework.passed - inProgress);
  const controlItems = localFramework.control_items ?? [];
  const slug = complianceFrameworkSlug(localFramework.name);
  const gapCount = notMet + inProgress;

  async function handleReevaluate() {
    const result = await reevaluateFramework.mutateAsync(slug);
    setLocalFramework(result.framework);
    setEvaluatedAt(result.evaluated_at);
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
              {evaluatedAt && (
                <p className="mt-2 text-[10px] text-muted-foreground">Re-evaluated {formatDateTime(evaluatedAt, timezone)}</p>
              )}
            </div>
            <CircularProgress score={localFramework.score} />
          </div>

          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Key controls</span>
            <span className="text-right">
              <span className={cn(notMet === 0 && inProgress === 0 ? "text-emerald-400" : "")}>
                {localFramework.passed} met
              </span>
              {inProgress > 0 && <span className="text-amber-400"> · {inProgress} in progress</span>}
              {notMet > 0 && <span className="text-red-400"> · {notMet} not met</span>}
            </span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{
                width: `${Math.max(0, Math.min(100, localFramework.score))}%`,
              }}
            />
          </div>

          <div className="mt-4 flex items-center gap-0.5">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  disabled={reevaluateFramework.isPending}
                  onClick={() => void handleReevaluate()}
                  aria-label="Re-evaluate framework"
                >
                  {reevaluateFramework.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Re-evaluate</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  onClick={() => exportFrameworkCsv(localFramework)}
                  aria-label="Export controls CSV"
                >
                  <Download className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Export CSV</TooltipContent>
            </Tooltip>
            {gapCount > 0 && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button size="icon" variant="ghost" className="h-8 w-8" asChild>
                    <Link href="/reports" aria-label={`${gapCount} open gaps`}>
                      <ClipboardList className="h-4 w-4" />
                    </Link>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {gapCount} gap{gapCount === 1 ? "" : "s"} — view reports
                </TooltipContent>
              </Tooltip>
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
