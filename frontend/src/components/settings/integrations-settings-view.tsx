"use client";

import { useState } from "react";
import { AlertWebhooksPanel } from "@/components/settings/alert-webhooks-panel";
import { PineconeSettingsPanel } from "@/components/settings/pinecone-settings";
import { VaultStatusPanel } from "@/components/settings/vault-status-panel";
import { SectionTabBar } from "@/components/shared/section-chrome";

const TABS = [
  { id: "vault", label: "Secrets & Vault" },
  { id: "pinecone", label: "Vector store" },
  { id: "webhooks", label: "Alert webhooks" },
] as const;

type IntegrationsTab = (typeof TABS)[number]["id"];

export function IntegrationsSettingsView() {
  const [tab, setTab] = useState<IntegrationsTab>("vault");

  return (
    <div className="space-y-6">
      <SectionTabBar tabs={TABS} active={tab} onChange={setTab} />
      {tab === "vault" && <VaultStatusPanel />}
      {tab === "pinecone" && <PineconeSettingsPanel />}
      {tab === "webhooks" && <AlertWebhooksPanel />}
    </div>
  );
}
