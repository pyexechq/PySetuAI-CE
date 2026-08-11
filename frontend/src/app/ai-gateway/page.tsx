import { AppShell } from "@/components/layout/app-shell";
import { AiGatewayView } from "@/components/ai-gateway/ai-gateway-view";

export default function AiGatewayPage() {
  return (
    <AppShell
      title="AI Gateway"
      description="OpenAI and Gemini compatible gateway with security inspection"
    >
      <AiGatewayView />
    </AppShell>
  );
}
