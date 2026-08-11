import { AppShell } from "@/components/layout/app-shell";
import { StudioView } from "@/components/studio/studio-view";

export default function StudioPage() {
  return (
    <AppShell
      title="Studio"
      description="Sandbox for prompt testing, policy dry-runs, and MCP tool simulation"
    >
      <StudioView />
    </AppShell>
  );
}
