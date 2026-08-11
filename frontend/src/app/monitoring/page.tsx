import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { MonitoringView } from "@/components/monitoring/monitoring-view";

export default function MonitoringPage() {
  return (
    <AppShell
      title="Monitoring"
      description="Gateway volume, AI security analytics, and distributed request traces"
    >
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading monitoring…</p>}>
        <MonitoringView />
      </Suspense>
    </AppShell>
  );
}
