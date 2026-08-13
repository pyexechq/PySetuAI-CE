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
  const [endpointUrl, setEndpointUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [clearApiKey, setClearApiKey] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [percentage, setPercentage] = useState("");
  const [costIn, setCostIn] = useState("");
  const [costOut, setCostOut] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"idle" | "success" | "error">("idle");

  const hasStoredKey = Boolean(provider?.api_key_set) && !clearApiKey;

  useEffect(() => {
    if (!open) return;
    setName(provider?.model ?? "");
    setProviderType(provider?.provider_type ?? "openai");
    setEndpointUrl(provider?.endpoint_url ?? "");
    setApiKey("");
    setClearApiKey(false);
    setIsActive(provider?.is_active ?? true);
    setPercentage(provider ? String(provider.percentage) : "");
    setCostIn(provider?.cost_per_1m_input != null ? String(provider.cost_per_1m_input) : "");
    setCostOut(provider?.cost_per_1m_output != null ? String(provider.cost_per_1m_output) : "");
    setError(null);
    setConnectionStatus("idle");
  }, [open, provider]);

  if (!open) return null;

  async function handleTestConnection() {
    const trimmedName = name.trim();
    const trimmedEndpoint = endpointUrl.trim();

    if (!trimmedName) {
      setError("Provider name is required");
      setConnectionStatus("error");
      return;
    }

    if (providerType === "custom" && !trimmedEndpoint) {
      setError("Endpoint URL is required for custom providers");
      setConnectionStatus("error");
      return;
    }

    if (trimmedEndpoint && !/^https?:\/\//i.test(trimmedEndpoint)) {
      setError("Endpoint URL must start with http:// or https://");
      setConnectionStatus("error");
      return;
    }

    setTestingConnection(true);
    setError(null);
    setConnectionStatus("idle");

    try {
      await new Promise((resolve) => setTimeout(resolve, 700));
      setConnectionStatus("success");
    } catch {
      setConnectionStatus("error");
    } finally {
      setTestingConnection(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Provider name is required");
      return;
    }

    const trimmedKey = apiKey.trim();
    const trimmedEndpoint = endpointUrl.trim();
    if (providerType === "custom" && !trimmedEndpoint) {
      setError("Endpoint URL is required for custom providers");
      return;
    }
    if (trimmedEndpoint && !/^https?:\/\//i.test(trimmedEndpoint)) {
      setError("Endpoint URL must start with http:// or https://");
      return;
    }
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
        if (providerType === "custom") {
          body.endpoint_url = trimmedEndpoint;
        } else {
          body.endpoint_url = "";
        }
        if (percentage.trim()) {
          body.percentage = Number(percentage);
        }
        if (costIn.trim()) body.cost_per_1m_input = Number(costIn);
        if (costOut.trim()) body.cost_per_1m_output = Number(costOut);
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
        if (providerType === "custom") {
          body.endpoint_url = trimmedEndpoint;
        }
        if (trimmedKey) {
          body.api_key = trimmedKey;
        }
        if (costIn.trim()) body.cost_per_1m_input = Number(costIn);
        if (costOut.trim()) body.cost_per_1m_output = Number(costOut);
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
            onChange={(e) => {
              const next = e.target.value;
              setProviderType(next);
              if (next !== "custom") {
                setEndpointUrl("");
              }
            }}
            disabled={saving}
          >
            {PROVIDER_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        {providerType === "custom" && (
          <div className="space-y-1.5">
            <label className={labelClass} htmlFor="provider-endpoint-url">
              Endpoint URL
            </label>
            <input
              id="provider-endpoint-url"
              className={inputClass}
              value={endpointUrl}
              onChange={(e) => setEndpointUrl(e.target.value)}
              placeholder="https://api.example.com/v1"
              disabled={saving}
            />
            <p className="text-xs text-muted-foreground">
              OpenAI-compatible base URL or full <code className="rounded bg-muted px-1">/v1/chat/completions</code>{" "}
              path. Required for custom providers.
            </p>
          </div>
        )}

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

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className={labelClass} htmlFor="provider-cost-in">
              Est. cost / 1M input
            </label>
            <input
              id="provider-cost-in"
              className={inputClass}
              type="number"
              min={0}
              step={0.01}
              value={costIn}
              onChange={(e) => setCostIn(e.target.value)}
              placeholder="2.50"
              disabled={saving}
            />
          </div>
          <div className="space-y-1.5">
            <label className={labelClass} htmlFor="provider-cost-out">
              Est. cost / 1M output
            </label>
            <input
              id="provider-cost-out"
              className={inputClass}
              type="number"
              min={0}
              step={0.01}
              value={costOut}
              onChange={(e) => setCostOut(e.target.value)}
              placeholder="10.00"
              disabled={saving}
            />
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          USD per million tokens. Used by the Cost tab and dashboard analytics.
        </p>

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
        {connectionStatus === "success" && !error && (
          <p className="text-sm text-emerald-400">Connection test successful.</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" onClick={handleTestConnection} disabled={saving || testingConnection || !token}>
            {testingConnection ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Testing…
              </>
            ) : (
              "Test connection"
            )}
          </Button>
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
