import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { McpToolChainsView } from "@/components/mcp-tool-chains/mcp-tool-chains-view";

function McpToolChainsFallback() {
  return (
    <div className="flex min-h-[240px] items-center justify-center text-sm text-muted-foreground">
      Loading MCP tool chains...
    </div>
  );
}

export default function McpToolChainsPage() {
  return (
    <AppShell
      title="MCP Tool Chains"
      description="Agent-to-agent and agent-to-tool chains, per-tool governance, and the attack surface map"
    >
      <Suspense fallback={<McpToolChainsFallback />}>
        <McpToolChainsView />
      </Suspense>
    </AppShell>
  );
}
