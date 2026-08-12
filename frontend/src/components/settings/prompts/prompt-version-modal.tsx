"use client";

import { useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAddPromptVersion } from "@/hooks/use-prompt-templates";
import type { PromptTemplate } from "@/lib/types/domain";

interface Props {
  template: PromptTemplate;
  onClose: () => void;
}

export function PromptVersionModal({ template, onClose }: Props) {
  const addVersionMutation = useAddPromptVersion();

  const [systemPrompt, setSystemPrompt] = useState(
    template.current_version?.system_prompt || ""
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    addVersionMutation.mutate(
      {
        id: template.id,
        data: { system_prompt: systemPrompt },
      },
      { onSuccess: onClose }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="w-full max-w-2xl overflow-hidden rounded-lg border border-border/60 bg-card shadow-lg animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
          <h2 className="text-lg font-semibold">
            Add Version — {template.name}
          </h2>
          <button onClick={onClose} className="rounded p-1 hover:bg-muted">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6">
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">New System Prompt</label>
                <span className="text-xs text-muted-foreground">
                  Use {"{{var}}"} for variables
                </span>
              </div>
              <textarea
                required
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                className="w-full min-h-[160px] rounded-md border border-input bg-background px-3 py-2 text-sm outline-none font-mono"
                placeholder="You are a helpful assistant for {{company_name}}..."
              />
            </div>
            <div className="rounded-md bg-muted p-3 text-sm text-muted-foreground">
              This will create Version {(template.current_version?.version || 0) + 1}. The new version will immediately become active for all gateway requests matching this template.
            </div>
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={addVersionMutation.isPending}>
              {addVersionMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Add Version
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
