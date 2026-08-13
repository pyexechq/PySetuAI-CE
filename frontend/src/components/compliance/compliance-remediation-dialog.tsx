"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AppModal } from "@/components/ui/dialog";
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
    <AppModal
      title={plan?.mode === "ai" ? "AI remediation plan" : "Manual remediation steps"}
      description={controlTitle ?? plan?.framework_name}
      onClose={onClose}
    >

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
    </AppModal>
  );
}
