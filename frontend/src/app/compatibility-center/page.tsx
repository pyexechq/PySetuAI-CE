import { AppShell } from "@/components/layout/app-shell";
import { CompatibilityCenterView } from "@/components/compatibility-center/compatibility-center-view";

export default function CompatibilityCenterPage() {
  return (
    <AppShell
      title="Compatibility Center"
      description="Universal AI Gateway model mappings, translation stats, and provider compatibility"
    >
      <CompatibilityCenterView />
    </AppShell>
  );
}
