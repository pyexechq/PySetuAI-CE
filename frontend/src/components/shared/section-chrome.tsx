"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface QuickLink {
  href: string;
  label: string;
  icon: LucideIcon;
}

export function QuickLinkPills({ links }: { links: readonly QuickLink[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {links.map((item) => {
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-card/50 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-border hover:text-foreground"
          >
            <Icon className="h-3.5 w-3.5" />
            {item.label}
            <ChevronRight className="h-3 w-3 opacity-50" />
          </Link>
        );
      })}
    </div>
  );
}

export function SectionTabBar<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: readonly { id: T; label: string }[];
  active: T;
  onChange: (tab: T) => void;
}) {
  return (
    <div className="flex gap-1 overflow-x-auto rounded-lg border border-border/60 bg-muted/30 p-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={cn(
            "shrink-0 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            active === tab.id
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function SectionHeading({ title }: { title: string }) {
  return <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</h2>;
}
