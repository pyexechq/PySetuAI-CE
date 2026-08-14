import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { AiGatewayView } from "@/components/ai-gateway/ai-gateway-view";

function AiGatewayFallback() {
  return (
    <div className="flex min-h-[240px] items-center justify-center text-sm text-muted-foreground">
      Loading AI Gateway…
    </div>
  );
}

export default function AiGatewayPage() {
  return (
    <AppShell
      title="AI Gateway"
      description="Secure ingress, protocol compatibility, and live gateway testing"
    >
      <Suspense fallback={<AiGatewayFallback />}>
        <AiGatewayView />
      </Suspense>
    </AppShell>
  );
}
