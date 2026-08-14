import { AlertWebhooksPanel } from "@/components/settings/alert-webhooks-panel";
import { PineconeSettingsPanel } from "@/components/settings/pinecone-settings";
import { VaultStatusPanel } from "@/components/settings/vault-status-panel";

export default function IntegrationsSettingsPage() {
  return (
    <div className="space-y-6">
      <VaultStatusPanel />
      <PineconeSettingsPanel />
      <AlertWebhooksPanel />
    </div>
  );
}
