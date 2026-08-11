import { IntegrationsSettings } from "@/components/settings/integrations-settings";
import { AlertWebhooksPanel } from "@/components/settings/alert-webhooks-panel";
import { VaultStatusPanel } from "@/components/settings/vault-status-panel";

export default function IntegrationsSettingsPage() {
  return (
    <div className="space-y-6">
      <IntegrationsSettings />
      <VaultStatusPanel />
      <AlertWebhooksPanel />
    </div>
  );
}
