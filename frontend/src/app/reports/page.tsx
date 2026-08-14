import { AppShell } from "@/components/layout/app-shell";
import { ReportsView } from "@/components/reports/reports-view";

export default function ReportsPage() {
  return (
    <AppShell
      title="Reports"
      description="Export snapshots, period summaries, and scheduled deliveries"
    >
      <ReportsView />
    </AppShell>
  );
}
