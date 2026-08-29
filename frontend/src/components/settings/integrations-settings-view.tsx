"use client";

import { useState } from "react";
import { AlertWebhooksPanel } from "@/components/settings/alert-webhooks-panel";
import { PineconeSettingsPanel } from "@/components/settings/pinecone-settings";
import { SmtpSettingsPanel } from "@/components/settings/smtp-settings-panel";
import { VaultStatusPanel } from "@/components/settings/vault-status-panel";
import { SectionTabBar } from "@/components/shared/section-chrome";

const TABS = [
  { id: "smtp", label: "Email & SMTP" },
  { id: "vault", label: "Secrets & Vault" },
  { id: "pinecone", label: "Vector store" },
  { id: "webhooks", label: "Alert webhooks" },
] as const;

type IntegrationsTab = (typeof TABS)[number]["id"];

export function IntegrationsSettingsView() {
  const [tab, setTab] = useState<IntegrationsTab>("smtp");

  return (
    <div className="space-y-6">
      <SectionTabBar tabs={TABS} active={tab} onChange={setTab} />
      {tab === "smtp" && <SmtpSettingsPanel />}
      {tab === "vault" && <VaultStatusPanel />}
      {tab === "pinecone" && <PineconeSettingsPanel />}
      {tab === "webhooks" && <AlertWebhooksPanel />}
    </div>
  );
}
