"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  findSettingsSection,
  settingsItemsForGroup,
  SETTINGS_GROUP_LABELS,
  type SettingsGroup,
} from "@/config/settings-navigation";
import { cn } from "@/lib/utils";

const GROUP_ORDER: SettingsGroup[] = ["general", "platform", "access"];

export function SettingsGroupNav() {
  const pathname = usePathname();
  const current = findSettingsSection(pathname);
  const group = current?.group ?? "general";
  const items = settingsItemsForGroup(group);

  return (
    <div className="space-y-3" data-help-id="settings-group-nav">
      <div className="flex flex-wrap gap-2">
        {GROUP_ORDER.map((g) => {
          const active = g === group;
          const firstHref = settingsItemsForGroup(g)[0]?.href ?? "/settings/organization";
          return (
            <Link
              key={g}
              href={active ? pathname : firstHref}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                active
                  ? "border-primary/40 bg-primary/10 text-primary"
                  : "border-border/60 text-muted-foreground hover:border-border hover:text-foreground"
              )}
            >
              {SETTINGS_GROUP_LABELS[g]}
            </Link>
          );
        })}
      </div>

      <div
        className="flex gap-1 overflow-x-auto rounded-lg border border-border/60 bg-muted/30 p-1"
        role="tablist"
        aria-label={`${SETTINGS_GROUP_LABELS[group]} settings`}
      >
        {items.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              role="tab"
              aria-selected={isActive}
              className={cn(
                "inline-flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
