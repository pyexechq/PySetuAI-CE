import { AppShell } from "@/components/layout/app-shell";
import { StudioView } from "@/components/studio/studio-view";

export default function StudioPage() {
  return (
    <AppShell
      title="Governance Sandbox"
      description="Sandbox for prompt testing, policy dry-runs, translation simulation, and MCP tool calls"
    >
      <StudioView />
    </AppShell>
  );
}
