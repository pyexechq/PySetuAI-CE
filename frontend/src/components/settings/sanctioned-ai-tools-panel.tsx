"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const TOOLS_QUERY_KEY = ["sanctioned-ai-tools"];

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "The request could not be completed.";
}

export function SanctionedAiToolsPanel() {
  const token = useAuthStore((state) => state.token);
  const queryClient = useQueryClient();
  const [name, setName] = useState("");

  const toolsQuery = useQuery({
    queryKey: [...TOOLS_QUERY_KEY, token],
    queryFn: () => api.listSanctionedAiTools(token!),
    enabled: Boolean(token),
  });

  const addMutation = useMutation({
    mutationFn: () => api.addSanctionedAiTool(token!, { name: name.trim() }),
    onSuccess: () => {
      setName("");
      queryClient.invalidateQueries({ queryKey: TOOLS_QUERY_KEY });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (toolId: string) => api.deleteSanctionedAiTool(token!, toolId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TOOLS_QUERY_KEY }),
  });

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (name.trim()) addMutation.mutate();
  };

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck className="h-4 w-4 text-emerald-500" />
          Sanctioned AI tools
        </CardTitle>
        <CardDescription>
          Maintain the tenant allowlist used to distinguish approved AI software from shadow-AI discoveries.
          Routine discovery remains logged; tools outside this list are surfaced as bypassed.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <form className="flex flex-col gap-2 sm:flex-row" onSubmit={submit}>
          <label className="sr-only" htmlFor="sanctioned-ai-tool-name">
            AI tool name
          </label>
          <input
            id="sanctioned-ai-tool-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Microsoft Copilot"
            maxLength={255}
            className="flex h-9 min-w-0 flex-1 rounded-md border border-input bg-background px-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/30"
          />
          <Button type="submit" size="sm" disabled={!name.trim() || addMutation.isPending}>
            {addMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Add tool
          </Button>
        </form>

        {(addMutation.isError || deleteMutation.isError || toolsQuery.isError) && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive" role="alert">
            {errorMessage(addMutation.error ?? deleteMutation.error ?? toolsQuery.error)}
          </div>
        )}

        {toolsQuery.isLoading ? (
          <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading sanctioned tools...
          </div>
        ) : toolsQuery.data?.length ? (
          <div className="space-y-2">
            {toolsQuery.data.map((tool) => (
              <div key={tool.id} className="flex flex-col gap-3 rounded-md border border-border/60 bg-background/50 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex min-w-0 items-center gap-3">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                  <div className="min-w-0">
                    <p className="truncate font-medium">{tool.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Added by {tool.added_by}
                      {tool.created_at ? ` · ${new Date(tool.created_at).toLocaleDateString()}` : ""}
                    </p>
                  </div>
                  <Badge variant="success" className="hidden shrink-0 sm:inline-flex">Sanctioned</Badge>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove ${tool.name} from sanctioned AI tools`}
                  title="Remove sanctioned tool"
                  disabled={deleteMutation.isPending}
                  onClick={() => {
                    if (window.confirm(`Remove ${tool.name} from the sanctioned AI allowlist?`)) {
                      deleteMutation.mutate(tool.id);
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-dashed border-border/60 p-8 text-center">
            <ShieldCheck className="mx-auto h-8 w-8 text-muted-foreground/50" />
            <p className="mt-3 font-medium">No sanctioned AI tools yet</p>
            <p className="mt-1 text-sm text-muted-foreground">Add the tools your organization has approved for use.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}