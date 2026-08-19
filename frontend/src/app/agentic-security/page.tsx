import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { AgenticSecurityView } from "@/components/agentic-security/agentic-security-view";

function AgenticSecurityFallback() {
  return (
    <div className="flex min-h-[240px] items-center justify-center text-sm text-muted-foreground">
      Loading agentic security...
    </div>
  );
}

export default function AgenticSecurityPage() {
  return (
    <AppShell
      title="Agentic Security"
      description="Anomaly detection, prompt-injection scanning, exfiltration, and the Guardian enforcement loop"
    >
      <Suspense fallback={<AgenticSecurityFallback />}>
        <AgenticSecurityView />
      </Suspense>
    </AppShell>
  );
}
