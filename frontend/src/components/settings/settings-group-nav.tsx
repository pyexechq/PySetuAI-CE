"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  findSettingsSection,
  settingsItemsForGroup,
  SETTINGS_GROUP_LABELS,
  type SettingsGroup,
} from "@/config/settings-navigation";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck, Sliders, Settings, Lock, Sparkles, Building2, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

const GROUP_ORDER: SettingsGroup[] = ["general", "platform", "access"];

const GROUP_ICONS: Record<SettingsGroup, typeof Building2> = {
  general: Building2,
  platform: Layers,
  access: Lock,
};

export function SettingsGroupNav() {
  const pathname = usePathname();
  const current = findSettingsSection(pathname);
  const group = current?.group ?? "general";
  const items = settingsItemsForGroup(group);

  return (
    <div className="space-y-6" data-help-id="settings-group-nav">
      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2 max-w-xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Tenant Mesh Active
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                HashiCorp Vault Encrypted
              </Badge>
            </div>

            <h1 className="text-2xl font-extrabold tracking-tight text-foreground">
              Enterprise Settings & System Controls
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Configure tenant profile branding, OIDC single sign-on providers, OPA Rego policy bundles, LLM Gateway credentials, and distributed edge mesh routing nodes.
            </p>
          </div>

          {/* Primary Category Switcher */}
          <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-card/80 border border-border/60 shadow-xs shrink-0">
            {GROUP_ORDER.map((g) => {
              const active = g === group;
              const firstHref = settingsItemsForGroup(g)[0]?.href ?? "/settings/organization";
              const Icon = GROUP_ICONS[g];
              return (
                <Link
                  key={g}
                  href={active ? pathname : firstHref}
                  className={cn(
                    "flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg transition-all whitespace-nowrap",
                    active
                      ? "bg-primary text-primary-foreground shadow-xs"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {SETTINGS_GROUP_LABELS[g]}
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      {/* ─── Secondary Sub-Tabs Strip (Horizontal scrolling on mobile) ────────── */}
      <div className="border-b border-border/60 pb-3">
        <div
          className="flex items-center gap-1.5 overflow-x-auto p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs"
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
                  "flex shrink-0 items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all whitespace-nowrap",
                  isActive
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
