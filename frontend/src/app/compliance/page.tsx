import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { ComplianceCenterView } from "@/components/compliance/compliance-center-view";

export default function CompliancePage() {
  return (
    <AppShell
      title="Compliance Center"
      description="Framework posture, evidence exports, and break-glass exemptions"
    >
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading compliance…</p>}>
        <ComplianceCenterView />
      </Suspense>
    </AppShell>
  );
}
