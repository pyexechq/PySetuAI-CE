import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { CopilotGovernanceView } from "@/components/copilot/copilot-governance-view";

function CopilotGovernanceFallback() {
  return (
    <div className="flex min-h-[240px] items-center justify-center text-sm text-muted-foreground">
      Loading Microsoft Copilot governance...
    </div>
  );
}

export default function MicrosoftCopilotPage() {
  return (
    <AppShell
      title="Microsoft Copilot"
      description="Copilot instances, connectors, and governance drift"
    >
      <Suspense fallback={<CopilotGovernanceFallback />}>
        <CopilotGovernanceView />
      </Suspense>
    </AppShell>
  );
}
