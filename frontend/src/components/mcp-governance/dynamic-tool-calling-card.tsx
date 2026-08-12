"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Save, Sparkles, Zap } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

export function DynamicToolCallingCard({ canEdit }: { canEdit: boolean }) {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["mcp-dynamic-tools", token],
    queryFn: () => api.getDynamicToolSettings(token!),
    enabled: Boolean(token),
  });

  const [enabled, setEnabled] = useState(false);
  const [maxTools, setMaxTools] = useState("8");
  const [previewQuery, setPreviewQuery] = useState("What is the weather in Mumbai tomorrow?");
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setEnabled(data.enabled);
      setMaxTools(String(data.max_tools));
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateDynamicToolSettings(token!, {
        enabled,
        max_tools: Math.max(1, parseInt(maxTools, 10) || 8),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-dynamic-tools"] });
    },
  });

  const previewMutation = useMutation({
    mutationFn: () =>
      api.previewDynamicTools(token!, {
        query: previewQuery,
        max_tools: Math.max(1, parseInt(maxTools, 10) || 8),
      }),
    onError: (err) => {
      setPreviewError(err instanceof Error ? err.message : "Preview failed");
    },
    onMutate: () => setPreviewError(null),
  });

  if (isLoading || !data) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading dynamic tool settings…
        </CardContent>
      </Card>
    );
  }

  const preview = previewMutation.data;

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Zap className="h-4 w-4 text-emerald-400" />
          Dynamic tool calling
        </CardTitle>
        <CardDescription>
          Rank MCP tools against each request and send at most N schemas to the model. Target: ≥50% fewer tool-description tokens vs the full catalog.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-border/60 bg-muted/10 px-3 py-2.5">
            <p className="text-[11px] text-muted-foreground">Catalog tools</p>
            <p className="text-lg font-semibold tabular-nums">{formatNumber(data.catalog_count)}</p>
          </div>
          <div className="rounded-lg border border-border/60 bg-muted/10 px-3 py-2.5">
            <p className="text-[11px] text-muted-foreground">Full catalog tokens</p>
            <p className="text-lg font-semibold tabular-nums">{formatNumber(data.catalog_tokens)}</p>
          </div>
          <div className="rounded-lg border border-border/60 bg-muted/10 px-3 py-2.5">
            <p className="text-[11px] text-muted-foreground">Max tools per request</p>
            <p className="text-lg font-semibold tabular-nums">{data.max_tools}</p>
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            disabled={!canEdit}
            className="rounded border-input"
          />
          Enable ranking and filtering on gateway ingress
        </label>

        <div className="max-w-xs space-y-2">
          <label className="text-sm font-medium">Max tools sent to model</label>
          <input
            type="number"
            min={1}
            max={64}
            value={maxTools}
            onChange={(e) => setMaxTools(e.target.value)}
            disabled={!canEdit || !enabled}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
          />
        </div>

        {canEdit ? (
          <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending} className="gap-2">
            {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save
          </Button>
        ) : null}

        <div className="space-y-2 border-t border-border/50 pt-4">
          <label className="text-sm font-medium">Preview token estimate</label>
          <textarea
            value={previewQuery}
            onChange={(e) => setPreviewQuery(e.target.value)}
            rows={2}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            placeholder="Type a sample user prompt…"
          />
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            disabled={!previewQuery.trim() || previewMutation.isPending}
            onClick={() => previewMutation.mutate()}
          >
            {previewMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            Preview ranking
          </Button>
          {previewError ? <p className="text-sm text-red-400">{previewError}</p> : null}
          {preview ? (
            <div className="space-y-2 rounded-lg border border-border/60 bg-muted/10 p-3 text-sm">
              <p>
                Selected {preview.selected_count} of {preview.catalog_count} tools · {preview.savings_pct.toFixed(1)}% token reduction
                ({formatNumber(preview.original_tokens)} → {formatNumber(preview.compressed_tokens)})
              </p>
              {preview.selected_names.length > 0 ? (
                <p className="text-xs text-muted-foreground">{preview.selected_names.join(", ")}</p>
              ) : (
                <p className="text-xs text-muted-foreground">No tools in catalog. Discover tools on a server first.</p>
              )}
            </div>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
