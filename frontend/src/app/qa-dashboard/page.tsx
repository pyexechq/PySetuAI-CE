import { AppShell } from "@/components/layout/app-shell";
import { QADashboardView } from "@/components/qa-dashboard/qa-dashboard-view";

export default function QADashboardPage() {
  return (
    <AppShell
      title="QA Dashboard"
      description="Record test results, track defects, and manage release readiness"
    >
      <QADashboardView />
    </AppShell>
  );
}
