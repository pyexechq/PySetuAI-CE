"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ChevronRight, HelpCircle, LifeBuoy, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useHelpChat } from "@/components/help/help-chat-provider";

export function HeaderHelpMenu() {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { openChat } = useHelpChat();

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  return (
    <div className="relative" ref={menuRef} data-help-id="header-help">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Help"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((prev) => !prev)}
      >
        <HelpCircle className="h-4 w-4" />
      </Button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-2 w-72 rounded-md border border-border bg-popover text-popover-foreground shadow-md animate-in fade-in-80 zoom-in-95"
        >
          <div className="border-b border-border p-3">
            <p className="text-sm font-medium">Help</p>
            <p className="mt-1 text-xs text-muted-foreground">
              AI guidance, articles, and platform policies.
            </p>
          </div>

          <div className="space-y-1 p-1">
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                openChat("What can I do on this page?");
              }}
              className="flex w-full items-start gap-3 rounded-sm px-2 py-2 text-left text-sm transition-colors hover:bg-muted"
            >
              <div className="rounded-md bg-primary/10 p-2">
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              <span className="min-w-0">
                <span className="font-medium leading-none">Ask AI Help</span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  Context-aware chat that highlights controls on this page
                </span>
              </span>
            </button>

            <Link
              href="/help"
              role="menuitem"
              onClick={() => setOpen(false)}
              className="flex items-start gap-3 rounded-sm px-2 py-2 text-sm transition-colors hover:bg-muted"
            >
              <div className="rounded-md bg-muted p-2">
                <LifeBuoy className="h-4 w-4 text-muted-foreground" />
              </div>
              <span className="min-w-0">
                <span className="flex items-center gap-1 font-medium leading-none">
                  Help & resources
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                </span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  Getting started, product guides, and trust policies
                </span>
              </span>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
