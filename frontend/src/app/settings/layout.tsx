"use client";

import { usePathname } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { SettingsGroupNav } from "@/components/settings/settings-group-nav";
import { SettingsSignOut } from "@/components/settings/settings-sections";
import { findSettingsSection } from "@/config/settings-navigation";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const section = findSettingsSection(pathname);

  return (
    <AppShell
      title={section?.label ?? "Settings"}
      description={section?.description ?? "Tenant configuration, RBAC, integrations, and platform settings"}
    >
      <div className="mx-auto max-w-6xl space-y-4">
        <SettingsGroupNav />
        <div className="min-w-0 space-y-6">
          {children}
          <SettingsSignOut />
        </div>
      </div>
    </AppShell>
  );
}
