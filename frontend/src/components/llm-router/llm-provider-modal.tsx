"use client";

import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError, api, type ApiLlmProviderCreateRequest, type ApiLlmProviderUpdateRequest, type ApiRoutingModel } from "@/lib/api";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50";
const labelClass = "text-sm font-medium";

const PROVIDER_TYPES = [
  { value: "openai", label: "OpenAI" },
  { value: "gemini", label: "Google Gemini" },
  { value: "anthropic", label: "Anthropic" },
  { value: "ollama", label: "Ollama" },
  { value: "azure", label: "Azure OpenAI" },
  { value: "custom", label: "Custom" },
];

function apiKeyPlaceholder(providerType: string, hasExisting: boolean): string {
  if (hasExisting) return "Enter new key to replace…";
  switch (providerType) {
    case "openai":
    case "azure":
    case "anthropic":
    case "custom":
      return "sk-…";
    case "gemini":
      return "AIza…";
    case "ollama":
      return "Optional — local Ollama usually needs no key";
    default:
      return "Enter API key";
  }
}

function apiKeyHint(providerType: string): string {
  switch (providerType) {
    case "openai":
      return "Stored per provider and synced to tenant OpenAI integration for gateway calls.";
    case "gemini":
      return "Stored per provider and synced to tenant Gemini integration for gateway calls.";
    case "azure":
    case "anthropic":
    case "custom":
      return "Stored encrypted at rest on this provider record and used for routing.";
    case "ollama":
      return "Leave blank if your Ollama instance does not require authentication.";
    default:
      return "";
  }
}

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

interface LlmProviderModalProps {
  open: boolean;
  provider: ApiRoutingModel | null;
  token: string | null;
  onClose: () => void;
  onSaved: () => void;
}

export function LlmProviderModal({ open, provider, token, onClose, onSaved }: LlmProviderModalProps) {
  const isEdit = provider !== null;
  const [name, setName] = useState("");
  const [providerType, setProviderType] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [clearApiKey, setClearApiKey] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [percentage, setPercentage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const hasStoredKey = Boolean(provider?.api_key_set) && !clearApiKey;

  useEffect(() => {
    if (!open) return;
    setName(provider?.model ?? "");
    setProviderType(provider?.provider_type ?? "openai");
    setApiKey("");
    setClearApiKey(false);
    setIsActive(provider?.is_active ?? true);
    setPercentage(provider ? String(provider.percentage) : "");
    setError(null);
  }, [open, provider]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Provider name is required");
      return;
    }

    const trimmedKey = apiKey.trim();
    if (!isEdit && providerType !== "ollama" && !trimmedKey && !clearApiKey) {
      setError("API key is required for this provider type");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      if (isEdit && provider) {
        const body: ApiLlmProviderUpdateRequest = {
          name: trimmedName,
          provider_type: providerType,
          is_active: isActive,
        };
        if (percentage.trim()) {
          body.percentage = Number(percentage);
        }
        if (clearApiKey) {
          body.api_key = "";
        } else if (trimmedKey) {
          body.api_key = trimmedKey;
        }
        await api.updateLlmProvider(token, provider.id, body);
      } else {
        const body: ApiLlmProviderCreateRequest = {
          name: trimmedName,
          provider_type: providerType,
          is_active: isActive,
        };
        if (trimmedKey) {
          body.api_key = trimmedKey;
        }
        await api.createLlmProvider(token, body);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save provider");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell
      title={isEdit ? "Edit LLM Provider" : "Register LLM Provider"}
      description={isEdit ? provider.model : "Add a model to the tenant routing registry"}
      onClose={onClose}
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-1.5">
          <label className={labelClass} htmlFor="provider-name">
            Model name
          </label>
          <input
            id="provider-name"
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="GPT-4o"
            disabled={saving}
          />
        </div>

        <div className="space-y-1.5">
          <label className={labelClass} htmlFor="provider-type">
            Provider type
          </label>
          <select
            id="provider-type"
            className={inputClass}
            value={providerType}
            onChange={(e) => setProviderType(e.target.value)}
            disabled={saving}
          >
            {PROVIDER_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <label className={labelClass} htmlFor="provider-api-key">
            API key
          </label>
          {hasStoredKey && provider?.api_key_masked && (
            <p className="text-xs text-muted-foreground">
              Saved: <span className="font-mono">{provider.api_key_masked}</span>
            </p>
          )}
          <input
            id="provider-api-key"
            className={inputClass}
            type="password"
            autoComplete="off"
            value={apiKey}
            onChange={(e) => {
              setApiKey(e.target.value);
              if (e.target.value.trim()) setClearApiKey(false);
            }}
            placeholder={apiKeyPlaceholder(providerType, hasStoredKey)}
            disabled={saving}
          />
          <p className="text-xs text-muted-foreground">{apiKeyHint(providerType)}</p>
          {isEdit && hasStoredKey && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => {
                setClearApiKey(true);
                setApiKey("");
              }}
              disabled={saving}
            >
              Remove stored key
            </Button>
          )}
        </div>

        {isEdit && (
          <div className="space-y-1.5">
            <label className={labelClass} htmlFor="provider-percentage">
              Routing share (%)
            </label>
            <input
              id="provider-percentage"
              className={inputClass}
              type="number"
              min={0}
              max={100}
              step={0.1}
              value={percentage}
              onChange={(e) => setPercentage(e.target.value)}
              disabled={saving}
            />
          </div>
        )}

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            disabled={saving}
          />
          Active in routing pool
        </label>

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
              "Register provider"
            )}
          </Button>
        </div>
      </form>
    </ModalShell>
  );
}
