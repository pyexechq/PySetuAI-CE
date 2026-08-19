"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import type { HelpChatMessage, HelpHighlight } from "@/lib/help-chat";
import { clearHelpSpotlights, collectVisibleHelpIds, highlightHelpTarget } from "@/lib/help-chat";

interface HelpChatContextValue {
  chatState: "idle" | "open" | "minimized";
  isOpen: boolean;
  messages: HelpChatMessage[];
  pageTitle: string;
  pageDescription?: string;
  activeHighlightId: string | null;
  openChat: (seed?: string) => void;
  minimizeChat: () => void;
  closeChat: () => void;
  setPageMeta: (title: string, description?: string) => void;
  addMessage: (message: HelpChatMessage) => void;
  setMessages: (messages: HelpChatMessage[]) => void;
  spotlight: (highlight: HelpHighlight) => void;
  clearSpotlight: () => void;
  getPageContext: () => {
    pathname: string;
    search: string;
    pageTitle: string;
    pageDescription?: string;
    visibleHelpIds: string[];
  };
}

const HelpChatContext = createContext<HelpChatContextValue | null>(null);

export function HelpChatProvider({
  children,
  initialTitle = "PySetu AI",
  initialDescription,
}: {
  children: ReactNode;
  initialTitle?: string;
  initialDescription?: string;
}) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const search = searchParams.toString();

  const [chatState, setChatState] = useState<"idle" | "open" | "minimized">("idle");
  const [messages, setMessages] = useState<HelpChatMessage[]>([]);
  const [pageTitle, setPageTitle] = useState(initialTitle);
  const [pageDescription, setPageDescription] = useState<string | undefined>(initialDescription);
  const [activeHighlightId, setActiveHighlightId] = useState<string | null>(null);

  const setPageMeta = useCallback((title: string, description?: string) => {
    setPageTitle(title);
    setPageDescription(description);
  }, []);

  const openChat = useCallback((seed?: string) => {
    setChatState("open");
    if (seed?.trim()) {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "user", content: seed.trim() },
      ]);
    }
  }, []);

  const minimizeChat = useCallback(() => {
    setChatState("minimized");
    clearHelpSpotlights();
    setActiveHighlightId(null);
  }, []);

  const closeChat = useCallback(() => {
    setChatState("idle");
    clearHelpSpotlights();
    setActiveHighlightId(null);
  }, []);

  const addMessage = useCallback((message: HelpChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const spotlight = useCallback((highlight: HelpHighlight) => {
    clearHelpSpotlights();
    const ok = highlightHelpTarget(highlight.helpId);
    if (ok) setActiveHighlightId(highlight.helpId);
  }, []);

  const clearSpotlight = useCallback(() => {
    clearHelpSpotlights();
    setActiveHighlightId(null);
  }, []);

  const getPageContext = useCallback(
    () => ({
      pathname,
      search: search ? `?${search}` : "",
      pageTitle,
      pageDescription,
      visibleHelpIds: collectVisibleHelpIds(),
    }),
    [pathname, search, pageTitle, pageDescription]
  );

  const value = useMemo(
    () => ({
      chatState,
      isOpen: chatState === "open",
      messages,
      pageTitle,
      pageDescription,
      activeHighlightId,
      openChat,
      minimizeChat,
      closeChat,
      setPageMeta,
      addMessage,
      setMessages,
      spotlight,
      clearSpotlight,
      getPageContext,
    }),
    [
      chatState,
      messages,
      pageTitle,
      pageDescription,
      activeHighlightId,
      openChat,
      minimizeChat,
      closeChat,
      setPageMeta,
      addMessage,
      spotlight,
      clearSpotlight,
      getPageContext,
    ]
  );

  return <HelpChatContext.Provider value={value}>{children}</HelpChatContext.Provider>;
}

export function useHelpChat() {
  const ctx = useContext(HelpChatContext);
  if (!ctx) throw new Error("useHelpChat must be used within HelpChatProvider");
  return ctx;
}
