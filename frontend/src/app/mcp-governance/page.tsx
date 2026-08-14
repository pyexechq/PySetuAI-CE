import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { McpGovernanceView } from "@/components/mcp-governance/mcp-governance-view";

function McpGovernanceFallback() {
  return (
    <div className="flex min-h-[240px] items-center justify-center text-sm text-muted-foreground">
      Loading MCP Governance…
    </div>
  );
}

export default function McpGovernancePage() {
  return (
    <AppShell
      title="MCP Governance"
      description="Manage MCP servers, policies, and the self-service portal"
    >
      <Suspense fallback={<McpGovernanceFallback />}>
        <McpGovernanceView />
      </Suspense>
    </AppShell>
  );
}
