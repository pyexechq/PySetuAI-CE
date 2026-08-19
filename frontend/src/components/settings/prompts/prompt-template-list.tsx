"use client";

import { useState } from "react";
import { Plus, Edit2, History, AlertTriangle, ShieldCheck } from "lucide-react";
import { usePromptTemplates } from "@/hooks/use-prompt-templates";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PromptTemplateModal } from "./prompt-template-modal";
import { PromptVersionModal } from "./prompt-version-modal";
import type { PromptTemplate } from "@/lib/types/domain";
import { formatDateTime } from "@/lib/date-utils";
import { usePreferencesStore } from "@/stores/preferences-store";

export function PromptTemplateList() {
  const timezone = usePreferencesStore((s) => s.timezone);
  const { data: templates, isLoading } = usePromptTemplates();
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplate | null>(null);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [versioningTemplate, setVersioningTemplate] = useState<PromptTemplate | null>(null);

  if (isLoading) {
    return <div className="p-8 text-center text-sm text-muted-foreground animate-pulse">Loading templates...</div>;
  }

  return (
    <div className="space-y-4" data-help-id="prompt-template-list">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">System Prompt Templates</h3>
        <Button
          data-help-id="prompt-create-button"
          onClick={() => {
            setEditingTemplate(null);
            setIsTemplateModalOpen(true);
          }}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          Create Template
        </Button>
      </div>

      <div className="rounded-md border border-border/60">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/60 bg-muted/20 text-left">
              <th className="px-4 py-3 font-medium text-muted-foreground">Name</th>
              <th className="px-4 py-3 font-medium text-muted-foreground">Alias</th>
              <th className="px-4 py-3 font-medium text-muted-foreground">Enforce Mode</th>
              <th className="px-4 py-3 font-medium text-muted-foreground">Version</th>
              <th className="px-4 py-3 font-medium text-muted-foreground">Last Updated</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {(!templates || templates.length === 0) ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                  No prompt templates found. Create one to enforce system prompts at the gateway.
                </td>
              </tr>
            ) : (
              templates.map((t) => (
                <tr key={t.id} className="hover:bg-muted/10">
                  <td className="px-4 py-3">
                    <div className="font-medium flex items-center gap-2">
                      {t.name}
                      {!t.is_active && <Badge variant="secondary" className="text-[10px]">Disabled</Badge>}
                    </div>
                    {t.description && <div className="text-xs text-muted-foreground mt-0.5 truncate max-w-[200px]">{t.description}</div>}
                  </td>
                  <td className="px-4 py-3">
                    {t.alias ? <code className="bg-muted px-1.5 py-0.5 rounded text-xs">{t.alias}</code> : <span className="text-muted-foreground">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    {t.enforce_mode === "strict" ? (
                      <Badge variant="destructive" className="gap-1 bg-destructive/10 text-destructive hover:bg-destructive/20 border-destructive/20">
                        <ShieldCheck className="h-3 w-3" />
                        Strict
                      </Badge>
                    ) : t.enforce_mode === "warn" ? (
                      <Badge variant="outline" className="gap-1 border-yellow-500/30 text-yellow-500">
                        <AlertTriangle className="h-3 w-3" />
                        Warn
                      </Badge>
                    ) : (
                      <Badge variant="secondary">Disabled</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    v{t.current_version?.version || 1}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatDateTime(t.updated_at, timezone)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setVersioningTemplate(t)}
                        title="Add Version"
                      >
                        <History className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditingTemplate(t);
                          setIsTemplateModalOpen(true);
                        }}
                        title="Edit Template"
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {isTemplateModalOpen && (
        <PromptTemplateModal
          template={editingTemplate}
          onClose={() => {
            setIsTemplateModalOpen(false);
            setEditingTemplate(null);
          }}
        />
      )}

      {versioningTemplate && (
        <PromptVersionModal
          template={versioningTemplate}
          onClose={() => setVersioningTemplate(null)}
        />
      )}
    </div>
  );
}
