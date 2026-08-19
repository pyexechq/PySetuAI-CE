import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { AgentInventoryView } from "@/components/agents/agent-inventory-view";

function AgentInventoryFallback() {
  return (
    <div className="flex min-h-[240px] items-center justify-center text-sm text-muted-foreground">
      Loading agent inventory…
    </div>
  );
}

export default function AgentsPage() {
  return (
    <AppShell
      title="Agent Inventory"
      description="Unified inventory of AI agents, their risk, and tool access"
    >
      <Suspense fallback={<AgentInventoryFallback />}>
        <AgentInventoryView />
      </Suspense>
    </AppShell>
  );
}
