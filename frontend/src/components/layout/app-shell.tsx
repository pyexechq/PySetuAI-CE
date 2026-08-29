"use client";

import { useState } from "react";
import Link from "next/link";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { HelpChatLayer } from "@/components/help/help-chat-layer";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";

interface AppShellProps {
  children: React.ReactNode;
  title: string;
  description?: string;
}

export function AppShell({ children, title, description }: AppShellProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <HelpChatLayer title={title} description={description}>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar className="hidden md:flex" />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <Header
            title={title}
            description={description}
            onMenuClick={() => setMobileNavOpen(true)}
          />
          <main className="relative min-h-0 flex-1 overflow-y-auto overflow-x-hidden flex flex-col justify-between p-4 md:p-6">
            <div className="flex-1 w-full max-w-full overflow-x-hidden">{children}</div>
            <footer className="mt-8 border-t border-border/50 pt-4 pb-2 text-xs text-muted-foreground flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span>© 2026 PySetu AI. All rights reserved.</span>
                <span className="inline-flex items-center rounded border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary uppercase leading-none">
                  Beta
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-4">
                <Link href="/terms" className="hover:text-foreground transition-colors">
                  Terms & Conditions
                </Link>
                <Link href="/privacy" className="hover:text-foreground transition-colors">
                  Privacy Policy
                </Link>
                <Link href="/legal/security" className="hover:text-foreground transition-colors">
                  Security & Trust
                </Link>
                <a href="mailto:hello@pysetu.io" className="hover:text-foreground transition-colors">
                  hello@pysetu.io
                </a>
              </div>
            </footer>
          </main>
        </div>
      </div>
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-64 p-0" hideClose>
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <Sidebar onNavigate={() => setMobileNavOpen(false)} />
        </SheetContent>
      </Sheet>
    </HelpChatLayer>
  );
}
