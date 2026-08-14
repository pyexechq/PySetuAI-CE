"use client";

import type { LucideIcon } from "lucide-react";
import {
  ArrowDown,
  ArrowRightLeft,
  Box,
  Cloud,
  DoorOpen,
  FileCheck,
  Plug,
  Route,
  Scale,
  Shield,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { AuditLogEntry } from "@/lib/types/domain";
import { parseUagTraceFromDetails } from "@/lib/uag-trace";
import { resolveAuditRoutingRule } from "@/lib/audit-routing";

interface TranslationTracePanelProps {
  entry: AuditLogEntry | null;
}

interface TraceStepConfig {
  label: string;
  value: string;
  icon: LucideIcon;
  accent: string;
  iconBg: string;
}

const GOVERNANCE_ACTION_META: Record<string, { icon: LucideIcon; className: string }> = {
  dlp: { icon: Shield, className: "border-rose-500/30 bg-rose-500/10 text-rose-400" },
  policy_engine: { icon: FileCheck, className: "border-amber-500/30 bg-amber-500/10 text-amber-400" },
  opa: { icon: Scale, className: "border-violet-500/30 bg-violet-500/10 text-violet-400" },
  egress_policy: { icon: DoorOpen, className: "border-sky-500/30 bg-sky-500/10 text-sky-400" },
};

function TraceConnector() {
  return (
    <div className="flex flex-col items-center py-1">
      <div className="h-3 w-px bg-gradient-to-b from-border/80 to-primary/40" />
      <ArrowDown className="h-3.5 w-3.5 text-primary/60" />
      <div className="h-3 w-px bg-gradient-to-b from-primary/40 to-border/80" />
    </div>
  );
}

function TraceStepCard({ step, isGovernance }: { step: TraceStepConfig; isGovernance?: boolean }) {
  const Icon = step.icon;
  const actions = isGovernance
    ? step.value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    : [];

  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border border-border/60 bg-background/40 px-3 py-2.5 shadow-sm",
        step.accent
      )}
    >
      <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", step.iconBg)}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{step.label}</p>
        {isGovernance && actions.length > 0 && actions[0] !== "none" ? (
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {actions.map((action) => {
              const meta = GOVERNANCE_ACTION_META[action] ?? {
                icon: Sparkles,
                className: "border-border/60 bg-muted/40 text-muted-foreground",
              };
              const ActionIcon = meta.icon;
              return (
                <span
                  key={action}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
                    meta.className
                  )}
                >
                  <ActionIcon className="h-3 w-3" />
                  {action.replace(/_/g, " ")}
                </span>
              );
            })}
          </div>
        ) : (
          <p className="mt-1 text-sm font-medium leading-snug">{step.value}</p>
        )}
      </div>
    </div>
  );
}

export function TranslationTracePanel({ entry }: TranslationTracePanelProps) {
  if (!entry) {
    return (
      <Card className="border-border/60 bg-gradient-to-br from-violet-500/5 via-card/50 to-sky-500/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/15 text-violet-400">
              <Route className="h-4 w-4" />
            </span>
            Translation trace
          </CardTitle>
          <CardDescription>Select an audit row with UAG activity to inspect the translation pipeline.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const { summary, trace } = parseUagTraceFromDetails(entry.details);
  const routing = resolveAuditRoutingRule(entry);

  if (!trace) {
    return (
      <Card className="border-border/60 bg-gradient-to-br from-violet-500/5 via-card/50 to-sky-500/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/15 text-violet-400">
              <Route className="h-4 w-4" />
            </span>
            Translation trace
          </CardTitle>
          <CardDescription>No UAG trace recorded for this entry.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">{summary}</p>
          {routing.rule && (
            <Badge variant="outline" className="gap-1 border-indigo-500/30 bg-indigo-500/10 text-indigo-300">
              <Route className="h-3 w-3" />
              {routing.label}: {routing.rule}
            </Badge>
          )}
        </CardContent>
      </Card>
    );
  }

  const steps: TraceStepConfig[] = [
    {
      label: "Source protocol",
      value: trace.source_protocol,
      icon: Plug,
      accent: "border-l-4 border-l-sky-500/70",
      iconBg: "bg-sky-500/15 text-sky-400",
    },
    {
      label: "Canonical model",
      value: trace.canonical_model,
      icon: Box,
      accent: "border-l-4 border-l-violet-500/70",
      iconBg: "bg-violet-500/15 text-violet-400",
    },
    {
      label: "Governance actions",
      value: trace.governance_actions?.length ? trace.governance_actions.join(", ") : "none",
      icon: Shield,
      accent: "border-l-4 border-l-amber-500/70",
      iconBg: "bg-amber-500/15 text-amber-400",
    },
    {
      label: "Target provider",
      value: `${trace.target_provider} (${trace.target_protocol})`,
      icon: Cloud,
      accent: "border-l-4 border-l-emerald-500/70",
      iconBg: "bg-emerald-500/15 text-emerald-400",
    },
    {
      label: "Translated response model",
      value: trace.requested_model,
      icon: ArrowRightLeft,
      accent: "border-l-4 border-l-cyan-500/70",
      iconBg: "bg-cyan-500/15 text-cyan-400",
    },
  ];

  return (
    <Card className="border-border/60 bg-gradient-to-br from-violet-500/5 via-card/50 to-emerald-500/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/15 text-violet-400 ring-1 ring-violet-500/20">
            <Route className="h-4 w-4" />
          </span>
          Translation trace
        </CardTitle>
        <CardDescription className="text-xs leading-relaxed">
          <span className="font-medium text-foreground/80">{entry.actor}</span>
          <span className="text-muted-foreground"> · {entry.timestamp}</span>
          <span className="mt-1 block text-muted-foreground">{summary}</span>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-0">
        {steps.map((step, index) => (
          <div key={step.label}>
            <TraceStepCard step={step} isGovernance={step.label === "Governance actions"} />
            {index < steps.length - 1 && <TraceConnector />}
          </div>
        ))}
        <div className="mt-4 flex flex-wrap gap-2 border-t border-border/50 pt-3">
          {routing.rule && (
            <Badge variant="outline" className="gap-1 border-indigo-500/30 bg-indigo-500/10 text-indigo-300">
              <Route className="h-3 w-3" />
              {routing.label}: {routing.rule}
            </Badge>
          )}
          {trace.policy_applied && (
            <Badge variant="outline" className="border-violet-500/30 bg-violet-500/10 text-violet-300">
              Policy: {trace.policy_applied}
            </Badge>
          )}
          {trace.compatibility_score != null && (
            <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
              Compatibility: {Math.round(trace.compatibility_score * 100)}%
            </Badge>
          )}
          {trace.translation_ms != null && (
            <Badge variant="outline" className="border-sky-500/30 bg-sky-500/10 text-sky-400">
              Translation: {trace.translation_ms} ms
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
