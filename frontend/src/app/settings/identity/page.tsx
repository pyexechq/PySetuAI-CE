import { IdentitySettingsPanel } from "@/components/settings/identity-settings-panel";
import { OidcProvidersPanel } from "@/components/settings/oidc-providers-panel";

export default function IdentitySettingsPage() {
  return (
    <div className="space-y-6">
      <IdentitySettingsPanel />
      <OidcProvidersPanel />
    </div>
  );
}
