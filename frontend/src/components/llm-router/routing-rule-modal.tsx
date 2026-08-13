"use client";

import { useEffect, useState } from "react";
import { Loader2, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppModal } from "@/components/ui/dialog";
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

// ── BL-087: Response format options ──────────────────────────────────────────
const RESPONSE_FORMAT_OPTIONS: { value: string; label: string; desc: string }[] = [
  { value: "openai",    label: "OpenAI Compatible (REST)",        desc: "Client receives a standard OpenAI chat completion response" },
  { value: "anthropic", label: "Anthropic Native",                desc: "Client receives Anthropic Messages API format" },
  { value: "vertex",    label: "Google Vertex AI Native",          desc: "Client receives Vertex AI GenerateContent format" },
  { value: "auto",      label: "Universal (Auto-Negotiated)",      desc: "Gateway detects and normalizes to the client's expected format" },
];


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
  targetModels: availableModels,
  token,
  onClose,
  onSaved,
}: RoutingRuleModalProps) {
  const isEdit = rule !== null;
  const [name, setName] = useState("");
  const [priority, setPriority] = useState("10");
  const [condition, setCondition] = useState("");
  const [selectedTargets, setSelectedTargets] = useState<string[]>([]);
  const [status, setStatus] = useState("draft");
  const [responseFormat, setResponseFormat] = useState("auto");  // BL-087
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(rule?.name ?? "");
    setPriority(String(rule?.priority ?? 10));
    setCondition(rule?.condition ?? "");
    setSelectedTargets(
      rule?.target_model
        ? rule.target_model.split(",").map((model) => model.trim()).filter(Boolean)
        : availableModels[0]
          ? [availableModels[0]]
          : []
    );
    setStatus(rule?.status ?? "draft");
    setResponseFormat(rule?.response_format ?? "auto");
    setError(null);
  }, [open, rule, availableModels]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;

    const trimmedName = name.trim();
    const trimmedCondition = condition.trim();
    const trimmedTargets = selectedTargets.map((model) => model.trim()).filter(Boolean);
    const priorityNum = Number(priority);

    if (!trimmedName || !trimmedCondition || trimmedTargets.length === 0) {
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
          target_model: trimmedTargets.join(", "),
          status,
          response_format: responseFormat as ApiRoutingRuleUpdateRequest["response_format"],
        };
        await api.updateRoutingRule(token, rule.id, body);
      } else {
        const body: ApiRoutingRuleCreateRequest = {
          name: trimmedName,
          priority: priorityNum,
          condition: trimmedCondition,
          target_model: trimmedTargets.join(", "),
          status,
          response_format: responseFormat as ApiRoutingRuleCreateRequest["response_format"],
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

  const selectedFormat = RESPONSE_FORMAT_OPTIONS.find((o) => o.value === responseFormat);

  return (
    <AppModal size="md"
      title={isEdit ? "Edit Routing Rule" : "Add Routing Rule"}
      description="Lower priority numbers run first. Use active status to enforce in the router."
      onClose={onClose}
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-1.5">
          <label className={labelClass} htmlFor="rule-name">Rule name</label>
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
            <label className={labelClass} htmlFor="rule-priority">Priority</label>
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
            <label className={labelClass} htmlFor="rule-status">Status</label>
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
            <label className={labelClass} htmlFor="rule-condition">Condition</label>
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
          <div className="flex items-center justify-between">
            <label className={labelClass} htmlFor="rule-target">Target model(s) / pool</label>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Weighted fan-out</span>
          </div>
          <div id="rule-target" className="flex min-h-11 flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-2.5 py-2">
            {selectedTargets.map((model) => (
              <span key={model} className="inline-flex items-center gap-1 rounded-md border border-primary/40 bg-primary/10 px-2 py-1 text-xs text-primary">
                {model}
                <button type="button" className="rounded-sm hover:bg-primary/20" onClick={() => setSelectedTargets((current) => current.filter((item) => item !== model))} aria-label={`Remove ${model}`}>
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            {selectedTargets.length === 0 && <span className="text-xs text-muted-foreground">Choose one or more models</span>}
          </div>
          {availableModels.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {availableModels.filter((model) => !selectedTargets.includes(model)).map((model) => (
                <button key={model} type="button" className="inline-flex items-center gap-1 rounded-md border border-border/60 px-2 py-1 text-xs text-muted-foreground hover:border-primary/50 hover:text-primary" onClick={() => setSelectedTargets((current) => [...current, model])}>
                <Plus className="h-3 w-3" /> {model}
                </button>
              ))}
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            Must match an active provider registered in the LLM Router.
          </p>
        </div>

        {/* ── BL-087: Client Response Format ─────────────────────────────── */}
        <div className="space-y-2 rounded-lg border border-border/60 bg-muted/20 p-4">
          <label className={labelClass} htmlFor="rule-response-format">
            Client Response Format
            <span className="ml-2 text-[10px] font-normal text-primary border border-primary/30 bg-primary/5 rounded px-1.5 py-0.5">
              BL-087
            </span>
          </label>
          <p className="text-xs text-muted-foreground -mt-1">
            The gateway translates the upstream provider response to this format before returning to the client.
          </p>
          <select
            id="rule-response-format"
            className={inputClass}
            value={responseFormat}
            onChange={(e) => setResponseFormat(e.target.value)}
            disabled={saving}
          >
            {RESPONSE_FORMAT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {selectedFormat && (
            <p className="text-xs text-muted-foreground italic">{selectedFormat.desc}</p>
          )}
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
    </AppModal>
  );
}
