"use client";

import { useState } from "react";
import { IdentitySettingsPanel } from "@/components/settings/identity-settings-panel";
import { OidcProvidersPanel } from "@/components/settings/oidc-providers-panel";
import { SectionTabBar } from "@/components/shared/section-chrome";

const TABS = [
  { id: "domains", label: "Login & domains" },
  { id: "oidc", label: "OIDC providers" },
] as const;

type IdentityTab = (typeof TABS)[number]["id"];

export function IdentitySettingsView() {
  const [tab, setTab] = useState<IdentityTab>("domains");

  return (
    <div className="space-y-6">
      <SectionTabBar tabs={TABS} active={tab} onChange={setTab} />
      {tab === "domains" && <IdentitySettingsPanel />}
      {tab === "oidc" && <OidcProvidersPanel />}
    </div>
  );
}
