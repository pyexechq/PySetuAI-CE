import { AppShell } from "@/components/layout/app-shell";
import { ReportsView } from "@/components/reports/reports-view";

export default function ReportsPage() {
  return (
    <AppShell
      title="Reports"
      description="Executive summaries, compliance exports, and scheduled governance reports"
    >
      <ReportsView />
    </AppShell>
  );
}
