import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { HelpResourcesView } from "@/components/help/help-resources-view";

export default function HelpPage() {
  return (
    <AppShell
      title="Help & resources"
      description="Onboarding, product guides, and trust policies for your tenant workspace"
    >
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading help…</p>}>
        <HelpResourcesView />
      </Suspense>
    </AppShell>
  );
}
