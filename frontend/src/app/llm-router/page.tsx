import { AppShell } from "@/components/layout/app-shell";
import { LlmRouterView } from "@/components/llm-router/llm-router-view";

export default function LlmRouterPage() {
  return (
    <AppShell
      title="LLM Router"
      description="Intelligently route requests to the best LLM for every prompt"
    >
      <LlmRouterView />
    </AppShell>
  );
}
