"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { SettingsTabs } from "@/components/settings/settings-nav";
import { SettingsSignOut } from "@/components/settings/settings-sections";
import { settingsNavItems } from "@/config/settings-navigation";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const section = settingsNavItems.find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`)
  );

  return (
    <AppShell
      title={section?.label ?? "Settings"}
      description={section?.description ?? "Tenant configuration, RBAC, integrations, and platform settings"}
    >
      <div className="mx-auto max-w-6xl space-y-4">
        <SettingsTabs />
        <div className="min-w-0 space-y-6">
          {children}
          <SettingsSignOut />
        </div>
      </div>
    </AppShell>
  );
}
