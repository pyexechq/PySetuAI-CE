import { AppShell } from "@/components/layout/app-shell";
import { McpPortalView } from "@/components/mcp-portal/mcp-portal-view";

export default function McpPortalPage() {
  return (
    <AppShell
      title="MCP Portal"
      description="Browse integrations and connect your personal MCP credentials"
    >
      <McpPortalView />
    </AppShell>
  );
}
