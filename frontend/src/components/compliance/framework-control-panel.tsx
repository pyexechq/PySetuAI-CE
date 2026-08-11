"use client";

import { CheckCircle2, CircleDashed, XCircle, ChevronDown, ChevronUp, Sparkles, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ApiComplianceControl } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useState } from "react";

const statusConfig = {
  met: {
    label: "Met",
    variant: "success" as const,
    icon: CheckCircle2,
    iconClass: "text-emerald-400",
  },
  not_met: {
    label: "Not met",
    variant: "destructive" as const,
    icon: XCircle,
    iconClass: "text-red-400",
  },
  in_progress: {
    label: "In progress",
    variant: "warning" as const,
    icon: CircleDashed,
    iconClass: "text-amber-400",
  },
};

function ControlRow({
  control,
  onManualFix,
  onAiAssist,
  remediationLoading,
}: {
  control: ApiComplianceControl;
  onManualFix?: (control: ApiComplianceControl) => void;
  onAiAssist?: (control: ApiComplianceControl) => void;
  remediationLoading?: boolean;
}) {
  const config = statusConfig[control.status] ?? statusConfig.in_progress;
  const Icon = config.icon;
  const showActions = control.status !== "met" && (onManualFix || onAiAssist);

  return (
    <div className="rounded-lg border border-border/60 bg-background/40 p-3">
      <div className="flex items-start gap-2">
        <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", config.iconClass)} />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-medium">{control.title}</p>
            <Badge variant={config.variant}>{config.label}</Badge>
            {control.helixguard_module && (
              <Badge variant="outline" className="font-normal">
                {control.helixguard_module}
              </Badge>
            )}
          </div>
          <div className="space-y-1 text-xs">
            <p>
              <span className="font-medium text-muted-foreground">Requirement: </span>
              {control.requirement}
            </p>
            {control.evidence && (
              <p>
                <span className="font-medium text-emerald-400/90">Evidence: </span>
                {control.evidence}
              </p>
            )}
            {control.status !== "met" && control.remediation && (
              <p>
                <span className="font-medium text-amber-400/90">Action needed: </span>
                {control.remediation}
              </p>
            )}
          </div>
          {showActions && (
            <div className="flex flex-wrap gap-2 pt-1">
              {onManualFix && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1 text-xs"
                  disabled={remediationLoading}
                  onClick={() => onManualFix(control)}
                >
                  <Wrench className="h-3 w-3" />
                  Manual fix
                </Button>
              )}
              {onAiAssist && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="h-7 gap-1 text-xs"
                  disabled={remediationLoading}
                  onClick={() => onAiAssist(control)}
                >
                  <Sparkles className="h-3 w-3" />
                  AI assist
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface FrameworkControlPanelProps {
  controls: ApiComplianceControl[];
  passed: number;
  inProgress: number;
  notMet: number;
  onManualFix?: (control: ApiComplianceControl) => void;
  onAiAssist?: (control: ApiComplianceControl) => void;
  remediationLoading?: boolean;
}

export function FrameworkControlPanel({
  controls,
  passed,
  inProgress,
  notMet,
  onManualFix,
  onAiAssist,
  remediationLoading,
}: FrameworkControlPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [filter, setFilter] = useState<"all" | ApiComplianceControl["status"]>("all");

  const filtered =
    filter === "all" ? controls : controls.filter((control) => control.status === filter);

  const grouped = {
    met: controls.filter((c) => c.status === "met"),
    in_progress: controls.filter((c) => c.status === "in_progress"),
    not_met: controls.filter((c) => c.status === "not_met"),
  };

  return (
    <div className="mt-4 border-t border-border/60 pt-4">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded-md bg-emerald-500/10 px-2 py-1 text-emerald-400">{passed} met</span>
        <span className="rounded-md bg-amber-500/10 px-2 py-1 text-amber-400">{inProgress} in progress</span>
        <span className="rounded-md bg-red-500/10 px-2 py-1 text-red-400">{notMet} not met</span>
      </div>

      <Button
        variant="outline"
        size="sm"
        className="mt-3 w-full justify-between"
        onClick={() => setExpanded((value) => !value)}
      >
        {expanded ? "Hide control details" : "View control requirements"}
        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </Button>

      {expanded && (
        <div className="mt-3 space-y-3">
          <div className="flex flex-wrap gap-2">
            {(
              [
                ["all", "All"],
                ["met", "Met"],
                ["in_progress", "In progress"],
                ["not_met", "Not met"],
              ] as const
            ).map(([key, label]) => (
              <Button
                key={key}
                variant={filter === key ? "default" : "outline"}
                size="sm"
                className="h-7 text-xs"
                onClick={() => setFilter(key)}
              >
                {label}
                {key !== "all" && ` (${grouped[key].length})`}
              </Button>
            ))}
          </div>

          <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
            {filtered.length === 0 ? (
              <p className="py-4 text-center text-xs text-muted-foreground">No controls in this category.</p>
            ) : (
              filtered.map((control) => (
                <ControlRow
                  key={control.id}
                  control={control}
                  onManualFix={onManualFix}
                  onAiAssist={onAiAssist}
                  remediationLoading={remediationLoading}
                />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
