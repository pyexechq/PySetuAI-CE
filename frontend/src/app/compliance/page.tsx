import { AppShell } from "@/components/layout/app-shell";
import { ComplianceCenterView } from "@/components/compliance/compliance-center-view";

export default function CompliancePage() {
  return (
    <AppShell
      title="Compliance Center"
      description="GDPR, HIPAA, SOC2, ISO27001, and NIST framework tracking"
    >
      <ComplianceCenterView />
    </AppShell>
  );
}
