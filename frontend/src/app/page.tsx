import { AppShell } from "@/components/layout/app-shell";
import { DashboardContent } from "@/components/dashboard/dashboard-content";

export default function DashboardPage() {
  return (
    <AppShell
      title="Executive Dashboard"
      description="Real-time overview of AI governance, security, and compliance"
    >
      <DashboardContent />
    </AppShell>
  );
}
