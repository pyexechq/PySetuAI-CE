"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Loader2, MapPin, Minus, Send, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useHelpChat } from "@/components/help/help-chat-provider";
import { normalizeHelpGuideHref } from "@/config/help-resources";
import { api, ApiError } from "@/lib/api";
import type { HelpChatMessage } from "@/lib/help-chat";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

const STARTER_PROMPTS = [
  "What can I do on this page?",
  "Highlight the main controls",
  "Where do I go next?",
];

function HelpAvatarButton({
  onClick,
  minimized,
  hasConversation,
  className,
}: {
  onClick: () => void;
  minimized?: boolean;
  hasConversation?: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      data-help-id="help-chat-launcher"
      onClick={onClick}
      aria-label={minimized ? "Restore AI help chat" : "Open AI help chat"}
      className={cn(
        "relative flex items-center justify-center rounded-full bg-gradient-to-br from-primary to-violet-600 text-primary-foreground shadow-lg transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        minimized ? "h-14 w-14" : "h-14 w-14",
        className
      )}
    >
      <Sparkles className="h-6 w-6" />
      {hasConversation && minimized && (
        <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-background text-[10px] font-bold text-primary ring-2 ring-primary">
          •
        </span>
      )}
    </button>
  );
}

export function HelpChatWidget() {
  const token = useAuthStore((s) => s.token);
  const {
    chatState,
    isOpen,
    openChat,
    minimizeChat,
    closeChat,
    messages,
    addMessage,
    getPageContext,
    spotlight,
    activeHighlightId,
    pageTitle,
  } = useHelpChat();

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const lastSentUserRef = useRef<string | null>(null);

  const { data: aiAssistSettings } = useQuery({
    queryKey: ["ai-assist-settings", token],
    queryFn: () => api.getAiAssistSettings(token!),
    enabled: Boolean(token),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!isOpen) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, isOpen]);

  useEffect(() => {
    if (!isOpen || !token || messages.length === 0) return;
    const last = messages[messages.length - 1];
    if (last.role !== "user" || last.id === lastSentUserRef.current) return;

    async function run() {
      lastSentUserRef.current = last.id;
      setLoading(true);
      setError(null);
      try {
        const ctx = getPageContext();
        const history = messages.slice(0, -1).map((m) => ({ role: m.role, content: m.content }));
        const result = await api.helpChat(token!, {
          message: last.content,
          pathname: ctx.pathname,
          search: ctx.search || null,
          page_title: ctx.pageTitle,
          page_description: ctx.pageDescription ?? null,
          visible_help_ids: ctx.visibleHelpIds,
          history,
        });

        const assistant: HelpChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.reply,
          highlights: result.highlights.map((h) => ({
            helpId: h.help_id,
            label: h.label,
            reason: h.reason,
          })),
          links: result.links.map((link) => ({
            ...link,
            href: normalizeHelpGuideHref(link.href),
          })),
          aiEnhanced: result.ai_enhanced,
        };
        addMessage(assistant);
        if (assistant.highlights?.[0]) {
          spotlight(assistant.highlights[0]);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to reach help assistant");
      } finally {
        setLoading(false);
      }
    }

    void run();
  }, [isOpen, messages, token, getPageContext, addMessage, spotlight]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    addMessage({ id: crypto.randomUUID(), role: "user", content: text });
  }

  function handleStarter(prompt: string) {
    if (loading) return;
    addMessage({ id: crypto.randomUUID(), role: "user", content: prompt });
  }

  const showAvatar = chatState === "idle" || chatState === "minimized";
  const hasConversation = messages.length > 0;

  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-[70] flex flex-col items-end gap-3">
      {isOpen && (
        <div
          className="pointer-events-auto flex w-[min(100vw-2.5rem,24rem)] flex-col overflow-hidden rounded-2xl border border-border/80 bg-background shadow-2xl"
          style={{ height: "min(32rem, calc(100vh - 6rem))" }}
        >
          <div className="flex items-center justify-between border-b border-border bg-gradient-to-r from-primary/10 to-violet-500/10 px-4 py-3">
            <div className="min-w-0">
              <p className="flex items-center gap-2 text-sm font-semibold">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/15">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                </span>
                AI Help
              </p>
              <p className="truncate pl-9 text-xs text-muted-foreground">{pageTitle}</p>
            </div>
            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                aria-label="Minimize help chat"
                onClick={minimizeChat}
              >
                <Minus className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                aria-label="Close help chat"
                onClick={closeChat}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {aiAssistSettings && !aiAssistSettings.available && (
            <div className="border-b border-amber-500/20 bg-amber-500/10 px-4 py-2 text-xs text-amber-700 dark:text-amber-200">
              Live AI is off — using guided responses.{" "}
              <Link href="/settings/ai-assist" className="underline">
                Enable AI Assist
              </Link>
            </div>
          )}

          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  I know which page you are on and can highlight buttons and sections to explain features.
                </p>
                <div className="flex flex-wrap gap-2">
                  {STARTER_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => handleStarter(prompt)}
                      className="rounded-full border border-border/60 px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-border hover:text-foreground"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "rounded-xl px-3 py-2 text-sm",
                  message.role === "user"
                    ? "ml-6 bg-primary text-primary-foreground"
                    : "mr-2 bg-muted/60 text-foreground"
                )}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                {message.role === "assistant" && message.highlights && message.highlights.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {message.highlights.map((highlight) => (
                      <button
                        key={highlight.helpId}
                        type="button"
                        onClick={() => spotlight(highlight)}
                        className={cn(
                          "flex w-full items-start gap-2 rounded-md border px-2 py-1.5 text-left text-xs transition-colors",
                          activeHighlightId === highlight.helpId
                            ? "border-primary/50 bg-primary/10 text-primary"
                            : "border-border/60 text-muted-foreground hover:border-border hover:text-foreground"
                        )}
                      >
                        <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        <span>
                          <span className="font-medium text-foreground">{highlight.label}</span>
                          {highlight.reason ? (
                            <span className="mt-0.5 block text-muted-foreground">{highlight.reason}</span>
                          ) : null}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
                {message.role === "assistant" && message.links && message.links.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {message.links.map((link) => (
                      <Link
                        key={`${link.href}-${link.label}`}
                        href={normalizeHelpGuideHref(link.href)}
                        className="text-xs font-medium text-primary hover:underline"
                        onClick={minimizeChat}
                      >
                        {link.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Thinking…
              </div>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSubmit} className="border-t border-border p-3">
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about this page…"
                className="flex-1 rounded-full border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
                disabled={loading}
              />
              <Button
                type="submit"
                size="icon"
                className="shrink-0 rounded-full"
                disabled={loading || !input.trim()}
                aria-label="Send message"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </form>
        </div>
      )}

      {showAvatar && (
        <div className="pointer-events-auto">
          <HelpAvatarButton
            minimized={chatState === "minimized"}
            hasConversation={hasConversation}
            onClick={() => openChat()}
          />
        </div>
      )}
    </div>
  );
}
