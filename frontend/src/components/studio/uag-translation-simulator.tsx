"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowDown, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function UagTranslationSimulator() {
  const token = useAuthStore((s) => s.token);
  const [prompt, setPrompt] = useState("Summarize our quarterly risk posture.");
  const [model, setModel] = useState("gpt-4o");
  const [result, setResult] = useState<Awaited<ReturnType<typeof api.simulateUagTranslation>> | null>(null);

  const simulate = useMutation({
    mutationFn: () =>
      api.simulateUagTranslation(token!, {
        model,
        messages: [{ role: "user", content: prompt }],
      }),
    onSuccess: (data) => setResult(data),
  });

  return (
    <Card className="border-border/60">
      <CardHeader>
        <CardTitle className="text-base">Translation simulator</CardTitle>
        <CardDescription>Preview OpenAI request → canonical → translated upstream payload.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            placeholder="Model (gpt-4o)"
          />
          <Button size="sm" disabled={simulate.isPending} onClick={() => simulate.mutate()}>
            {simulate.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Simulate translation"}
          </Button>
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        />

        {result && (
          <div className="space-y-3">
            <PipelineBlock title="Original request" data={result.original_request} />
            <div className="flex justify-center text-muted-foreground">
              <ArrowDown className="h-4 w-4" />
            </div>
            <PipelineBlock title="Canonical request" data={result.canonical} />
            <div className="flex justify-center text-muted-foreground">
              <ArrowDown className="h-4 w-4" />
            </div>
            <PipelineBlock title="Translated request" data={result.translated_request} />
            <PipelineBlock title="Trace" data={result.trace} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PipelineBlock({ title, data }: { title: string; data: unknown }) {
  return (
    <div className="rounded-md border border-border/60 bg-muted/20 p-3">
      <p className="mb-2 text-xs font-medium text-muted-foreground">{title}</p>
      <pre className="overflow-x-auto text-xs">{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}
