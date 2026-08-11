"use client";

import { ArrowDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AuditLogEntry } from "@/lib/types/domain";
import { parseUagTraceFromDetails } from "@/lib/uag-trace";

interface TranslationTracePanelProps {
  entry: AuditLogEntry | null;
}

export function TranslationTracePanel({ entry }: TranslationTracePanelProps) {
  if (!entry) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="text-base">Translation trace</CardTitle>
          <CardDescription>Select an audit row with UAG activity to inspect the translation pipeline.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const { summary, trace } = parseUagTraceFromDetails(entry.details);
  if (!trace) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="text-base">Translation trace</CardTitle>
          <CardDescription>No UAG trace recorded for this entry.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{summary}</p>
        </CardContent>
      </Card>
    );
  }

  const steps = [
    { label: "Source protocol", value: trace.source_protocol },
    { label: "Canonical model", value: trace.canonical_model },
    {
      label: "Governance actions",
      value: trace.governance_actions?.length ? trace.governance_actions.join(", ") : "none",
    },
    { label: "Target provider", value: `${trace.target_provider} (${trace.target_protocol})` },
    { label: "Translated response model", value: trace.requested_model },
  ];

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="text-base">Translation trace</CardTitle>
        <CardDescription>
          {entry.actor} · {entry.timestamp} · {summary}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {steps.map((step, index) => (
          <div key={step.label}>
            <div className="rounded-md border border-border/60 px-3 py-2">
              <p className="text-xs font-medium text-muted-foreground">{step.label}</p>
              <p className="mt-1 text-sm">{step.value}</p>
            </div>
            {index < steps.length - 1 && (
              <div className="flex justify-center py-1 text-muted-foreground">
                <ArrowDown className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}
        <div className="flex flex-wrap gap-2 pt-1">
          {trace.policy_applied && <Badge variant="outline">Policy: {trace.policy_applied}</Badge>}
          {trace.compatibility_score != null && (
            <Badge variant="outline">Compatibility: {Math.round(trace.compatibility_score * 100)}%</Badge>
          )}
          {trace.translation_ms != null && (
            <Badge variant="outline">Translation: {trace.translation_ms} ms</Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
