import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { AuditExplorerView } from "@/components/audit-explorer/audit-explorer-view";

export default function AuditExplorerPage() {
  return (
    <AppShell
      title="Audit Explorer"
      description="Search, inspect, and export AI infrastructure audit events"
    >
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading audit explorer…</p>}>
        <AuditExplorerView />
      </Suspense>
    </AppShell>
  );
}
