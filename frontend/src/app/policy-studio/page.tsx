import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PolicyStudioLayout } from "@/components/policy-studio/policy-studio-layout";

export default function PolicyStudioPage() {
  return (
    <AppShell title="Policy Studio" description="Design, visualize and enforce governance policies">
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading policy studio…</p>}>
        <PolicyStudioLayout />
      </Suspense>
    </AppShell>
  );
}
