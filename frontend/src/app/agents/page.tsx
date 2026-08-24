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
      title="Agents & Endpoints"
      description="Unified inventory of AI agents, endpoints, and tool access"
    >
      <Suspense fallback={<AgentInventoryFallback />}>
        <AgentInventoryView />
      </Suspense>
    </AppShell>
  );
}
