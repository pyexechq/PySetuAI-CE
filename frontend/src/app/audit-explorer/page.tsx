import { AppShell } from "@/components/layout/app-shell";
import { AuditExplorerView } from "@/components/audit-explorer/audit-explorer-view";

export default function AuditExplorerPage() {
  return (
    <AppShell
      title="Audit Explorer"
      description="Search, inspect and analyze all AI infrastructure requests"
    >
      <AuditExplorerView />
    </AppShell>
  );
}
