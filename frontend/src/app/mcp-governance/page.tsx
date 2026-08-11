import { AppShell } from "@/components/layout/app-shell";
import { McpGovernanceView } from "@/components/mcp-governance/mcp-governance-view";

export default function McpGovernancePage() {
  return (
    <AppShell
      title="MCP Governance"
      description="Manage, secure and govern all MCP servers and tools"
    >
      <McpGovernanceView />
    </AppShell>
  );
}
