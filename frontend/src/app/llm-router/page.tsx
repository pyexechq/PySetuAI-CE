import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { LlmRouterView } from "@/components/llm-router/llm-router-view";

function LlmRouterFallback() {
  return (
    <div className="flex min-h-[240px] items-center justify-center text-sm text-muted-foreground">
      Loading LLM Router…
    </div>
  );
}

export default function LlmRouterPage() {
  return (
    <AppShell
      title="LLM Router"
      description="Route requests, manage models, and configure gateway translation"
    >
      <Suspense fallback={<LlmRouterFallback />}>
        <LlmRouterView />
      </Suspense>
    </AppShell>
  );
}
