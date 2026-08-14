import { AiAssistSettings } from "@/components/settings/ai-assist-settings";
import { TenantLlmProviderSettings } from "@/components/settings/tenant-llm-provider-settings";

export default function AiAssistSettingsPage() {
  return (
    <div className="space-y-6">
      <AiAssistSettings />
      <TenantLlmProviderSettings />
    </div>
  );
}
