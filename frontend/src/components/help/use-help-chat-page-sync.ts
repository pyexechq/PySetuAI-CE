"use client";

import { useEffect } from "react";
import { useHelpChat } from "@/components/help/help-chat-provider";

export function useHelpChatPageSync(title: string, description?: string) {
  const { setPageMeta } = useHelpChat();

  useEffect(() => {
    setPageMeta(title, description);
  }, [title, description, setPageMeta]);
}
