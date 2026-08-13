"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppModal } from "@/components/ui/dialog";
import { useCreatePromptTemplate, useUpdatePromptTemplate } from "@/hooks/use-prompt-templates";
import type { PromptTemplate } from "@/lib/types/domain";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50";
const labelClass = "text-sm font-medium";

interface Props {
  template: PromptTemplate | null;
  onClose: () => void;
}

export function PromptTemplateModal({ template, onClose }: Props) {
  const isEditing = !!template;
  const createMutation = useCreatePromptTemplate();
  const updateMutation = useUpdatePromptTemplate();

  const [name, setName] = useState(template?.name || "");
  const [alias, setAlias] = useState(template?.alias || "");
  const [description, setDescription] = useState(template?.description || "");
  const [enforceMode, setEnforceMode] = useState<"strict" | "warn" | "disabled">(
    template?.enforce_mode || "warn"
  );
  const [systemPrompt, setSystemPrompt] = useState(template?.current_version?.system_prompt || "");

  const isPending = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isEditing) {
      updateMutation.mutate(
        {
          id: template.id,
          data: {
            name,
            alias: alias || null,
            description: description || null,
            enforce_mode: enforceMode,
          },
        },
        { onSuccess: onClose }
      );
    } else {
      createMutation.mutate(
        {
          name,
          alias: alias || null,
          description: description || null,
          enforce_mode: enforceMode,
          system_prompt: systemPrompt,
        },
        { onSuccess: onClose }
      );
    }
  };

  return (
    <AppModal
      title={isEditing ? "Edit Template" : "Create Prompt Template"}
      onClose={onClose}
      size="xl"
    >
        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className={labelClass}>Template Name</label>
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className={inputClass}
                  placeholder="e.g., Customer Support V1"
                />
              </div>
              <div className="space-y-2">
                <label className={labelClass}>Alias (Optional)</label>
                <input
                  value={alias}
                  onChange={(e) => setAlias(e.target.value)}
                  className={inputClass}
                  placeholder="e.g., support-v1"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className={labelClass}>Description (Optional)</label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className={inputClass}
                placeholder="Brief description of when this prompt is used..."
              />
            </div>

            <div className="space-y-2">
              <label className={labelClass}>Enforce Mode</label>
              <select
                value={enforceMode}
                onChange={(e) => setEnforceMode(e.target.value as any)}
                className={inputClass}
              >
                <option value="warn">Warn (Log ad-hoc prompts, don't block)</option>
                <option value="strict">Strict (Block ad-hoc prompts, HTTP 403)</option>
                <option value="disabled">Disabled (Do not evaluate this template)</option>
              </select>
              <p className="text-xs text-muted-foreground">
                In strict mode, gateway requests without a managed template are blocked.
              </p>
            </div>

            {!isEditing && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className={labelClass}>Initial System Prompt</label>
                  <span className="text-xs text-muted-foreground">Use {"{{var}}"} for variables</span>
                </div>
                <textarea
                  required
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm outline-none font-mono"
                  placeholder="You are a helpful assistant for {{company_name}}..."
                />
              </div>
            )}
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEditing ? "Save Changes" : "Create Template"}
            </Button>
          </div>
        </form>
    </AppModal>
  );
}
