"use client";

import Link from "next/link";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ApiComplianceRemediationResponse } from "@/lib/api";

interface ComplianceRemediationDialogProps {
  open: boolean;
  loading: boolean;
  plan: ApiComplianceRemediationResponse | null;
  controlTitle?: string;
  onClose: () => void;
}

export function ComplianceRemediationDialog({
  open,
  loading,
  plan,
  controlTitle,
  onClose,
}: ComplianceRemediationDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">
              {plan?.mode === "ai" ? "AI remediation plan" : "Manual remediation steps"}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">{controlTitle ?? plan?.framework_name}</p>
          </div>
          <Button variant="outline" size="sm" className="h-8 w-8 p-0" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {loading && (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating remediation plan…
          </div>
        )}

        {!loading && plan && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{plan.framework_name}</Badge>
              {plan.estimated_effort && <Badge variant="secondary">Effort: {plan.estimated_effort}</Badge>}
              {plan.mode === "ai" && (
                <Badge variant={plan.ai_generated ? "default" : "outline"}>
                  {plan.ai_generated ? "AI generated" : "PySetu playbook"}
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">{plan.summary}</p>
            <ol className="list-decimal space-y-2 pl-5 text-sm">
              {plan.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            {plan.manual_route && (
              <Button asChild variant="secondary" className="gap-2">
                <Link href={plan.manual_route}>Open PySetu module</Link>
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
