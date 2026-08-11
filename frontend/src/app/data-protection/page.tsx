import { AppShell } from "@/components/layout/app-shell";
import { DataProtectionView } from "@/components/data-protection/data-protection-view";

export default function DataProtectionPage() {
  return (
    <AppShell
      title="Data Protection Center"
      description="PII detection, DLP, redaction, and data classification"
    >
      <DataProtectionView />
    </AppShell>
  );
}
