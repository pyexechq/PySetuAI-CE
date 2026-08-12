"use client";

import { useState } from "react";
import { Play, Loader2, Sparkles, ShieldAlert, Scissors, Eye, X } from "lucide-react";
import { useTestCustomIntent } from "@/hooks/use-custom-intents";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface CustomIntentTesterModalProps {
  onClose: () => void;
}

export function CustomIntentTesterModal({ onClose }: CustomIntentTesterModalProps) {
  const testMutation = useTestCustomIntent();
  const [testPrompt, setTestPrompt] = useState("Please wire transfer funds to external account 987654321");

  const getActionBadge = (act: string) => {
    if (act === "block") {
      return (
        <Badge variant="destructive" className="gap-1 bg-destructive/10 text-destructive border-destructive/20">
          <ShieldAlert className="h-3 w-3" />
          Block
        </Badge>
      );
    }
    if (act === "redact") {
      return (
        <Badge variant="outline" className="gap-1 border-purple-500/40 text-purple-400">
          <Scissors className="h-3 w-3" />
          Redact
        </Badge>
      );
    }
    return (
      <Badge variant="secondary" className="gap-1">
        <Eye className="h-3 w-3" />
        Monitor
      </Badge>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="w-full max-w-lg border-border/60 bg-card shadow-lg relative">
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-4 top-4"
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </Button>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Play className="h-4 w-4 text-primary" />
            Intent Classifier Tester
          </CardTitle>
          <CardDescription>
            Test prompt content against active classifiers to verify policy outcomes.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Test Prompt Input</label>
            <textarea
              value={testPrompt}
              onChange={(e) => setTestPrompt(e.target.value)}
              rows={4}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-ring focus-visible:ring-2"
              placeholder="Enter prompt to evaluate..."
            />
          </div>

          <Button
            className="w-full gap-2"
            disabled={!testPrompt.trim() || testMutation.isPending}
            onClick={() => testMutation.mutate({ prompt: testPrompt })}
          >
            {testMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Evaluate Prompt
          </Button>

          {testMutation.data && (
            <div className="rounded-md border border-border/60 p-4 bg-muted/20 space-y-3 text-sm mt-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Evaluation Result:</span>
                {getActionBadge(testMutation.data.action)}
              </div>
              {testMutation.data.matched ? (
                <div className="space-y-2">
                  <p className="text-muted-foreground">Matched Classifiers:</p>
                  {testMutation.data.matches.map((m) => (
                    <div key={m.intent_id} className="p-3 rounded bg-background border border-border/40 space-y-1">
                      <div className="flex justify-between font-medium">
                        <span>{m.intent_name}</span>
                        <span>Score: {Math.round(m.score * 100)}%</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Matched words: {m.matched_keywords.join(", ")}
                      </p>
                    </div>
                  ))}
                  {testMutation.data.modified_prompt && (
                    <div className="mt-3 space-y-1">
                      <p className="font-medium text-purple-400">Redacted Output:</p>
                      <div className="p-3 rounded bg-background font-mono text-xs whitespace-pre-wrap">
                        {testMutation.data.modified_prompt}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground">No custom intent policy violations detected.</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
