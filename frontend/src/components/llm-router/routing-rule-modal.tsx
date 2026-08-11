"use client";

import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  RoutingConditionHelpButton,
  type RoutingConditionHelpExample,
} from "@/components/llm-router/routing-condition-help";
import {
  ApiError,
  api,
  type ApiRoutingRule,
  type ApiRoutingRuleCreateRequest,
  type ApiRoutingRuleUpdateRequest,
} from "@/lib/api";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50";
const labelClass = "text-sm font-medium";

function ModalShell({
  title,
  description,
  onClose,
  children,
}: {
  title: string;
  description?: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{title}</h2>
            {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
          </div>
          <Button variant="outline" size="sm" className="h-8 w-8 p-0" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}

interface RoutingRuleModalProps {
  open: boolean;
  rule: ApiRoutingRule | null;
  targetModels: string[];
  token: string | null;
  onClose: () => void;
  onSaved: () => void;
}

export function RoutingRuleModal({
  open,
  rule,
  targetModels,
  token,
  onClose,
  onSaved,
}: RoutingRuleModalProps) {
  const isEdit = rule !== null;
  const [name, setName] = useState("");
  const [priority, setPriority] = useState("10");
  const [condition, setCondition] = useState("");
  const [targetModel, setTargetModel] = useState("");
  const [status, setStatus] = useState("draft");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(rule?.name ?? "");
    setPriority(String(rule?.priority ?? 10));
    setCondition(rule?.condition ?? "");
    setTargetModel(rule?.target_model ?? targetModels[0] ?? "");
    setStatus(rule?.status ?? "draft");
    setError(null);
  }, [open, rule, targetModels]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;

    const trimmedName = name.trim();
    const trimmedCondition = condition.trim();
    const trimmedTarget = targetModel.trim();
    const priorityNum = Number(priority);

    if (!trimmedName || !trimmedCondition || !trimmedTarget) {
      setError("Name, condition, and target model are required");
      return;
    }
    if (!Number.isFinite(priorityNum) || priorityNum < 1) {
      setError("Priority must be a positive number");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      if (isEdit && rule) {
        const body: ApiRoutingRuleUpdateRequest = {
          name: trimmedName,
          priority: priorityNum,
          condition: trimmedCondition,
          target_model: trimmedTarget,
          status,
        };
        await api.updateRoutingRule(token, rule.id, body);
      } else {
        const body: ApiRoutingRuleCreateRequest = {
          name: trimmedName,
          priority: priorityNum,
          condition: trimmedCondition,
          target_model: trimmedTarget,
          status,
        };
        await api.createRoutingRule(token, body);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save routing rule");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell
      title={isEdit ? "Edit Routing Rule" : "Add Routing Rule"}
      description="Lower priority numbers run first. Use active status to enforce in the router."
      onClose={onClose}
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-1.5">
          <label className={labelClass} htmlFor="rule-name">
            Rule name
          </label>
          <input
            id="rule-name"
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Code tasks → Claude"
            disabled={saving}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label className={labelClass} htmlFor="rule-priority">
              Priority
            </label>
            <input
              id="rule-priority"
              type="number"
              min={1}
              className={inputClass}
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              disabled={saving}
            />
          </div>
          <div className="space-y-1.5">
            <label className={labelClass} htmlFor="rule-status">
              Status
            </label>
            <select
              id="rule-status"
              className={inputClass}
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              disabled={saving}
            >
              <option value="active">active</option>
              <option value="draft">draft</option>
              <option value="disabled">disabled</option>
            </select>
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <label className={labelClass} htmlFor="rule-condition">
              Condition
            </label>
            <RoutingConditionHelpButton
              onApplyExample={(example: RoutingConditionHelpExample) => {
                setCondition(example.condition);
                if (!name.trim() && example.title) {
                  setName(example.title);
                }
              }}
            />
          </div>
          <input
            id="rule-condition"
            className={`${inputClass} font-mono text-xs`}
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            placeholder="task.type == 'code_review'"
            disabled={saving}
          />
          <p className="text-xs text-muted-foreground">
            Supports comparisons on dotted paths (<code className="text-[11px]">task.type</code>,{" "}
            <code className="text-[11px]">sla.latency_ms</code>, <code className="text-[11px]">input.has_image</code>
            ), <code className="text-[11px]">default</code>, and <code className="text-[11px]">and</code> /{" "}
            <code className="text-[11px]">or</code>. Gateway requests with <code className="text-[11px]">model: auto</code>{" "}
            evaluate active rules using <code className="text-[11px]">routing_context</code>.
          </p>
        </div>

        <div className="space-y-1.5">
          <label className={labelClass} htmlFor="rule-target">
            Target model
          </label>
          {targetModels.length > 0 ? (
            <select
              id="rule-target"
              className={inputClass}
              value={targetModel}
              onChange={(e) => setTargetModel(e.target.value)}
              disabled={saving}
            >
              {targetModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          ) : (
            <input
              id="rule-target"
              className={inputClass}
              value={targetModel}
              onChange={(e) => setTargetModel(e.target.value)}
              placeholder="GPT-4o"
              disabled={saving}
            />
          )}
          <p className="text-xs text-muted-foreground">
            Must match an active provider registered in the LLM Router.
          </p>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving || !token}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving…
              </>
            ) : isEdit ? (
              "Save changes"
            ) : (
              "Add rule"
            )}
          </Button>
        </div>
      </form>
    </ModalShell>
  );
}
