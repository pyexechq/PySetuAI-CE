import { AppShell } from "@/components/layout/app-shell";
import { ObservabilityView } from "@/components/observability/observability-view";

export default function ObservabilityPage() {
  return (
    <AppShell
      title="Observability"
      description="AI request tracing, latency metrics, and distributed spans from audit telemetry"
    >
      <ObservabilityView />
    </AppShell>
  );
}
