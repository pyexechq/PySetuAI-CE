"use client";

import { useState } from "react";
import { AiAssistSettings } from "@/components/settings/ai-assist-settings";
import { TenantLlmProviderSettings } from "@/components/settings/tenant-llm-provider-settings";
import { SectionTabBar } from "@/components/shared/section-chrome";

const TABS = [
  { id: "assist", label: "Platform AI Assist" },
  { id: "providers", label: "Tenant LLM defaults" },
] as const;

type AiAssistTab = (typeof TABS)[number]["id"];

export function AiAssistSettingsView() {
  const [tab, setTab] = useState<AiAssistTab>("assist");

  return (
    <div className="space-y-6">
      <SectionTabBar tabs={TABS} active={tab} onChange={setTab} />
      {tab === "assist" && <AiAssistSettings />}
      {tab === "providers" && <TenantLlmProviderSettings />}
    </div>
  );
}
