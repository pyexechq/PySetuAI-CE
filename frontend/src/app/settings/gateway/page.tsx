import { Suspense } from "react";

import { GatewaySettingsSection } from "@/components/settings/gateway-settings";

export default function GatewaySettingsPage() {
  return (
    <Suspense>
      <GatewaySettingsSection />
    </Suspense>
  );
}
