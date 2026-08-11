"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { settingsNavItems } from "@/config/settings-navigation";
import { cn } from "@/lib/utils";

function navLinkClass(isActive: boolean, compact = false) {
  return cn(
    compact
      ? "inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
      : "flex items-start gap-3 rounded-lg px-3 py-2.5 transition-colors",
    isActive
      ? compact
        ? "bg-primary text-primary-foreground shadow-sm"
        : "bg-primary/10 text-primary"
      : compact
        ? "bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground"
        : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
  );
}

export function SettingsTabs() {
  const pathname = usePathname();

  return (
    <div
      className="sticky top-0 z-20 rounded-xl border border-border/60 bg-card/90 p-2 shadow-sm backdrop-blur md:hidden"
      role="tablist"
      aria-label="Settings sections"
    >
      <div className="flex gap-1 overflow-x-auto pb-1">
        {settingsNavItems.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              role="tab"
              aria-selected={isActive}
              className={navLinkClass(isActive, true)}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
