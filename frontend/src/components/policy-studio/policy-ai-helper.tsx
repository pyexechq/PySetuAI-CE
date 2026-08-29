"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Sparkles, Wand2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import type { PolicyRule } from "@/lib/types/domain";

type SuggestedRule = PolicyRule & { rationale?: string };
const SUGGESTIONS_PER_PAGE = 2;

export function PolicyAiHelper({
  token,
  policyName,
  existingRules,
  canEdit,
  onApplySuggestion,
}: {
  token: string | null;
  policyName?: string;
  existingRules: PolicyRule[];
  canEdit: boolean;
  onApplySuggestion: (rule: PolicyRule) => void;
}) {
  const [goal, setGoal] = useState("");
  const [summary, setSummary] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestedRule[]>([]);
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
      const result = await api.assistPolicyBuilding(token, {
        goal: goal.trim(),
        policy_name: policyName,
        existing_rule_names: existingRules.map((rule) => rule.name),
      });
      setSummary(result.summary);
      setAiEnhanced(Boolean(result.ai_enhanced));
      setSuggestions(
        result.suggestions.map((item) => ({
          id: item.id,
          name: item.name,
          condition: item.condition,
          action: item.action,
          severity: item.severity as PolicyRule["severity"],
          enabled: item.enabled,
          rationale: item.rationale,
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
    <Card className="w-full lg:w-[340px] shrink-0 flex flex-col overflow-hidden border-border/60 bg-card/50">
      <CardHeader className="pb-3 shrink-0">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Sparkles className="h-4 w-4 text-indigo-400" />
          AI Helper
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Describe what you want to enforce. PySetu suggests rule conditions you can add to{" "}
          {policyName ? `"${policyName}"` : "the selected policy"}.
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
              className="rounded-xl border border-border/60 bg-muted/20 px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground text-center w-full line-clamp-2 min-h-[32px] leading-tight flex items-center justify-center"
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
          placeholder='e.g. "Block jailbreak, DAN mode, and attempts to reveal the system prompt"'
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
          {loading ? "Thinking…" : "Suggest rules"}
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
              {paginatedSuggestions.map((rule) => (
                <div key={rule.id} className="rounded-lg border border-border/60 bg-muted/20 p-3">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-xs font-medium">{rule.name}</span>
                  <Badge variant="outline" className="text-[10px]">
                    {rule.action}
                  </Badge>
                  <Badge variant="secondary" className="text-[10px] capitalize">
                    {rule.severity}
                  </Badge>
                </div>
                <code className="mt-1 block break-all font-mono text-[10px] text-muted-foreground">{rule.condition}</code>
                {rule.rationale && <p className="mt-1 text-[11px] text-muted-foreground">{rule.rationale}</p>}
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-2 h-7 w-full text-xs"
                  onClick={() => onApplySuggestion(rule)}
                  disabled={!canEdit}
                >
                  Add to policy
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
            Tip: select a policy first, then describe security or compliance goals. Use the{" "}
            <span className="font-medium text-foreground">?</span> icon in Add/Edit Rule for condition syntax help.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
