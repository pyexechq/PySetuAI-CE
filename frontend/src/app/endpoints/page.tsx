import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { EndpointSecurityView } from "@/components/endpoints/endpoint-security-view";

function EndpointSecurityFallback() {
  return (
    <div className="flex min-h-[240px] items-center justify-center text-sm text-muted-foreground">
      Loading endpoint security…
    </div>
  );
}

export default function EndpointsPage() {
  return (
    <AppShell
      title="Endpoint Security"
      description="Devices running the PySetu endpoint agent and their status"
    >
      <Suspense fallback={<EndpointSecurityFallback />}>
        <EndpointSecurityView />
      </Suspense>
    </AppShell>
  );
}
