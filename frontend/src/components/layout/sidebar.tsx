"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Building2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { mainNavGroups } from "@/config/navigation";
import { settingsNavItems } from "@/config/settings-navigation";
import { BrandingLogo } from "@/components/branding/branding-logo";
import { TenantBrandingSync } from "@/components/branding/tenant-branding-sync";
import { tenantBrandName, tenantBrandTagline, useTenantStore } from "@/stores/tenant-store";
import { useAuthStore, canAccessRoute, canAccessTenantModule } from "@/stores/auth-store";
const SETTINGS_ROOT = "/settings";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { currentTenant } = useTenantStore();
  const { user } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(pathname.startsWith(SETTINGS_ROOT));

  useEffect(() => {
    if (pathname.startsWith(SETTINGS_ROOT)) {
      setSettingsOpen(true);
    }
  }, [pathname]);

  const visibleNavGroups = mainNavGroups
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) =>
          user?.role &&
          canAccessRoute(user.role, item.href) &&
          canAccessTenantModule(currentTenant, item.href)
      ),
    }))
    .filter((group) => group.items.length > 0);

  const settingsActive = pathname.startsWith(SETTINGS_ROOT);
  const brandName = tenantBrandName(currentTenant);
  const brandTagline = tenantBrandTagline(currentTenant);

  return (
    <>
      <TenantBrandingSync />
      <aside
      className={cn(
        "flex h-screen flex-col border-r border-border bg-sidebar transition-all duration-300",
        collapsed ? "w-[72px]" : "w-64"
      )}
    >
      <div className="flex h-16 items-center gap-3 border-b border-border px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-primary">
          <BrandingLogo logoUrl={currentTenant.logoUrl} alt={brandName} iconClassName="h-5 w-5 text-primary-foreground" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-foreground">{brandName}</p>
            <p className="truncate text-[10px] text-muted-foreground">{brandTagline}</p>
          </div>
        )}
      </div>

      {!collapsed && (
        <div className="border-b border-border px-4 py-3">
          <div className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2">
            <Building2 className="h-4 w-4 text-muted-foreground" />
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Tenant</p>
              <p className="truncate text-sm font-medium">{currentTenant.name}</p>
            </div>
          </div>
        </div>
      )}

      <nav className="flex-1 space-y-4 overflow-y-auto p-3">
        {visibleNavGroups.map((group) => (
          <div key={group.label} className="space-y-1">
            {!collapsed && (
              <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/80">
                {group.label}
              </p>
            )}
            {group.items.map((item) => {
              const isSettings = item.href === SETTINGS_ROOT;
              const isActive = isSettings
                ? settingsActive
                : pathname === item.href || pathname.startsWith(`${item.href}/`);
              const Icon = item.icon;

              if (isSettings) {
                return (
                  <div key={item.href} className="space-y-1">
                    <div className="flex items-center gap-1">
                      <Link
                        href="/settings/organization"
                        title={collapsed ? item.title : undefined}
                        className={cn(
                          "flex min-w-0 flex-1 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                          settingsActive
                            ? "bg-primary/15 text-primary"
                            : "text-muted-foreground hover:bg-accent hover:text-foreground"
                        )}
                      >
                        <Icon className="h-4 w-4 shrink-0" />
                        {!collapsed && <span className="truncate">{item.title}</span>}
                      </Link>
                      {!collapsed && (
                        <button
                          type="button"
                          onClick={() => setSettingsOpen((open) => !open)}
                          className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
                          aria-expanded={settingsOpen}
                          aria-label={settingsOpen ? "Collapse settings menu" : "Expand settings menu"}
                        >
                          <ChevronDown
                            className={cn("h-4 w-4 transition-transform", settingsOpen && "rotate-180")}
                          />
                        </button>
                      )}
                    </div>
                    {!collapsed && settingsOpen && (
                      <ul className="ml-4 space-y-0.5 border-l border-border/60 pl-2">
                        {settingsNavItems.map((sub) => {
                          const subActive =
                            pathname === sub.href || pathname.startsWith(`${sub.href}/`);
                          const SubIcon = sub.icon;
                          return (
                            <li key={sub.href}>
                              <Link
                                href={sub.href}
                                className={cn(
                                  "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
                                  subActive
                                    ? "bg-primary/10 text-primary"
                                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                                )}
                              >
                                <SubIcon className="h-3.5 w-3.5 shrink-0" />
                                {sub.label}
                              </Link>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                );
              }

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={collapsed ? item.title : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/15 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span className="truncate">{item.title}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="shrink-0 border-t border-border p-3">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex w-full items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>
    </aside>
    </>
  );
}
