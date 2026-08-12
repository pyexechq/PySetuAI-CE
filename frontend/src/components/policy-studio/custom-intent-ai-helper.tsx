"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Sparkles, Wand2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import type { ApiCustomIntentAssistSuggestion } from "@/lib/api";

type SuggestedIntent = ApiCustomIntentAssistSuggestion & { id: string };
const SUGGESTIONS_PER_PAGE = 2;

export function CustomIntentAiHelper({
  token,
  canEdit,
  onApplySuggestion,
}: {
  token: string | null;
  canEdit: boolean;
  onApplySuggestion: (intent: ApiCustomIntentAssistSuggestion) => void;
}) {
  const [goal, setGoal] = useState("");
  const [summary, setSummary] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestedIntent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiEnhanced, setAiEnhanced] = useState(false);
  const [suggestionPage, setSuggestionPage] = useState(1);

  const { data: aiAssistSettings } = useQuery({
    queryKey: ["ai-assist-settings", token],
    queryFn: () => api.getAiAssistSettings(token!),
    enabled: Boolean(token),
    staleTime: 60_000,
  });

  async function handleSuggest() {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.assistCustomIntentBuilding(token, goal.trim());
      setSummary(result.summary);
      setAiEnhanced(Boolean(result.ai_enhanced));
      setSuggestions(
        result.suggestions.map((item) => ({
          id: crypto.randomUUID(),
          name: item.name,
          description: item.description,
          action: item.action,
          keywords: item.keywords,
          confidence_threshold: item.confidence_threshold,
        })),
      );
      setSuggestionPage(1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to generate suggestions");
      setSuggestions([]);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }

  function handleQuickPrompt(prompt: string) {
    setGoal(prompt);
  }

  const totalSuggestionPages = Math.ceil(suggestions.length / SUGGESTIONS_PER_PAGE);
  const paginatedSuggestions = suggestions.slice(
    (suggestionPage - 1) * SUGGESTIONS_PER_PAGE,
    suggestionPage * SUGGESTIONS_PER_PAGE
  );

  return (
    <Card className="w-full flex flex-col overflow-hidden border-border/60 bg-card/50">
      <CardHeader className="pb-3 shrink-0">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Sparkles className="h-4 w-4 text-indigo-400" />
          AI Helper
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Describe what you want to detect or enforce. PySetu suggests custom intents with keywords.
        </p>
        {aiAssistSettings && !aiAssistSettings.available && (
          <p className="mt-2 text-[11px] text-amber-300">
            Live AI enhancement is off.{" "}
            <Link href="/settings/ai-assist" className="underline">
              Configure AI Assist
            </Link>{" "}
            in Settings (Tenant Admin).
          </p>
        )}
        {aiAssistSettings?.available && (
          <p className="mt-2 text-[11px] text-emerald-400">
            AI Assist active ({aiAssistSettings.provider} · {aiAssistSettings.model}).
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-3 pt-0 flex-1 flex flex-col overflow-hidden">
        <div className="grid grid-cols-2 gap-1.5 shrink-0">
          {[
            "Block prompt injection",
            "Prevent jailbreak attempts",
            "Redact US SSN and phone",
            "Enforce EU data residency",
          ].map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="rounded-full border border-border/60 bg-muted/20 px-2 py-0.5 text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground text-center w-full truncate"
              onClick={() => handleQuickPrompt(prompt)}
              disabled={!canEdit}
            >
              {prompt}
            </button>
          ))}
        </div>

        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          rows={4}
          placeholder='e.g. "Detect requests for external wire transfers or bank account details"'
          className="w-full shrink-0 rounded-md border border-input bg-background px-3 py-2 text-xs outline-none ring-ring focus-visible:ring-2"
          disabled={!canEdit}
        />

        <Button
          size="sm"
          className="w-full shrink-0 gap-1.5"
          onClick={handleSuggest}
          disabled={!canEdit || !token || loading}
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5" />}
          {loading ? "Thinking…" : "Suggest intents"}
        </Button>

        {error && <p className="text-xs text-red-400 shrink-0">{error}</p>}
        {summary && (
          <p className="text-xs text-emerald-400 shrink-0">
            {summary}
            {aiEnhanced ? " · Enhanced with tenant AI Assist" : ""}
          </p>
        )}

        {suggestions.length > 0 && (
          <div className="space-y-3 flex-1 flex flex-col overflow-hidden min-h-0">
            <div className="flex-1 space-y-2 overflow-y-auto min-h-0">
              {paginatedSuggestions.map((intent) => (
                <div key={intent.id} className="rounded-lg border border-border/60 bg-muted/20 p-3">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-xs font-medium">{intent.name}</span>
                  <Badge variant="outline" className="text-[10px]">
                    {intent.action}
                  </Badge>
                  <Badge variant="secondary" className="text-[10px] capitalize">
                    {Math.round(intent.confidence_threshold * 100)}% Match
                  </Badge>
                </div>
                {intent.description && <p className="mt-1 text-[11px] text-muted-foreground">{intent.description}</p>}
                <div className="flex flex-wrap gap-1 mt-2">
                  {intent.keywords.map((kw) => (
                    <Badge key={kw} variant="outline" className="text-[9px] bg-muted/30">
                      {kw}
                    </Badge>
                  ))}
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-2 h-7 w-full text-xs"
                  onClick={() => onApplySuggestion(intent)}
                  disabled={!canEdit}
                >
                  Add to intents
                </Button>
              </div>
            ))}
            </div>
            {totalSuggestionPages > 1 && (
              <div className="flex items-center justify-between pt-1 shrink-0">
                <p className="text-[10px] text-muted-foreground">
                  Showing {(suggestionPage - 1) * SUGGESTIONS_PER_PAGE + 1} to {Math.min(suggestionPage * SUGGESTIONS_PER_PAGE, suggestions.length)} of {suggestions.length}
                </p>
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-6 px-2 text-[10px]"
                    onClick={() => setSuggestionPage((p) => Math.max(1, p - 1))}
                    disabled={suggestionPage === 1}
                  >
                    Prev
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-6 px-2 text-[10px]"
                    onClick={() => setSuggestionPage((p) => Math.min(totalSuggestionPages, p + 1))}
                    disabled={suggestionPage === totalSuggestionPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {!loading && suggestions.length === 0 && !summary && (
          <p className="text-[11px] text-muted-foreground">
            Tip: describe the topics or sensitive data you want to classify, and PySetu will suggest keywords for your custom intent.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
