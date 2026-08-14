import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { MonitoringView } from "@/components/monitoring/monitoring-view";

export default function MonitoringPage() {
  return (
    <AppShell
      title="Monitoring"
      description="Gateway health, security analytics, and traces"
    >
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading monitoring…</p>}>
        <MonitoringView />
      </Suspense>
    </AppShell>
  );
}
