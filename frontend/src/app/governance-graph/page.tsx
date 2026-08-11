import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { GovernanceGraphView } from "@/components/governance/governance-graph-view";

export default function GovernanceGraphPage() {
  return (
    <AppShell title="Governance Graph" description="Visualize policy flows, model routing, and MCP dependencies">
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading governance graph…</p>}>
        <GovernanceGraphView />
      </Suspense>
    </AppShell>
  );
}
