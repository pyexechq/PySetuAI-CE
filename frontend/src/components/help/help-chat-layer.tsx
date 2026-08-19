"use client";

import { Suspense, type ReactNode } from "react";
import { HelpChatWidget } from "@/components/help/help-chat-widget";
import { HelpChatProvider } from "@/components/help/help-chat-provider";
import { useHelpChatPageSync } from "@/components/help/use-help-chat-page-sync";

function HelpChatLayerInner({
  children,
  title,
  description,
}: {
  children: ReactNode;
  title: string;
  description?: string;
}) {
  useHelpChatPageSync(title, description);

  return (
    <>
      {children}
      <HelpChatWidget />
    </>
  );
}

export function HelpChatLayer({
  children,
  title,
  description,
}: {
  children: ReactNode;
  title: string;
  description?: string;
}) {
  return (
    <Suspense fallback={children}>
      <HelpChatProvider initialTitle={title} initialDescription={description}>
        <HelpChatLayerInner title={title} description={description}>
          {children}
        </HelpChatLayerInner>
      </HelpChatProvider>
    </Suspense>
  );
}
