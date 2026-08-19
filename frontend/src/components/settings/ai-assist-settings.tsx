"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Save, Sparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiAiAssistSettings } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const FEATURE_LIST = [
  "Policy Studio AI Helper",
  "Compliance Center AI assist",
  "Dashboard metric insights",
  "Context-aware help chat",
];

const DEFAULT_MODELS: Record<ApiAiAssistSettings["provider"], string> = {
  openai: "gpt-4o-mini",
  gemini: "gemini-1.5-flash",
  groq: "llama-3.1-8b-instant",
  ollama: "llama3.2",
  vllm: "meta-llama/Llama-3.1-8B-Instruct",
  custom: "gpt-4o-mini",
};

const DEFAULT_BASE_URLS: Partial<Record<ApiAiAssistSettings["provider"], string>> = {
  ollama: "http://localhost:11434",
  vllm: "http://localhost:8000/v1",
  custom: "http://localhost:8000/v1",
};

const LOCAL_PROVIDERS = new Set<ApiAiAssistSettings["provider"]>(["ollama", "vllm", "custom"]);

const FALLBACK_PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  gemini: "Google Gemini",
  groq: "Groq",
  ollama: "Ollama (air-gap)",
  vllm: "vLLM (air-gap)",
  custom: "Custom OpenAI-compatible (air-gap)",
};

const EMPTY: ApiAiAssistSettings = {
  enabled: false,
  provider: "openai",
  model: "gpt-4o-mini",
  api_key_set: false,
  api_key_masked: null,
  base_url: null,
  available: false,
  uses_gateway_fallback: false,
  credential_source: "none",
  supported_providers: ["openai", "gemini", "groq", "ollama", "vllm", "custom"],
  provider_labels: FALLBACK_PROVIDER_LABELS,
  features: [],
  air_gap_mode: false,
};

function providerLabel(settings: ApiAiAssistSettings, id: string) {
  return settings.provider_labels?.[id] ?? FALLBACK_PROVIDER_LABELS[id] ?? id;
}

function isLocalProvider(provider: ApiAiAssistSettings["provider"]) {
  return LOCAL_PROVIDERS.has(provider);
}

function defaultModelFor(provider: ApiAiAssistSettings["provider"]) {
  return DEFAULT_MODELS[provider];
}

export function AiAssistSettings() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const canEdit = user?.role === "tenant_admin" || user?.role === "platform_admin";

  const { data, isLoading } = useQuery({
    queryKey: ["ai-assist-settings", token],
    queryFn: () => api.getAiAssistSettings(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const settings = data ?? EMPTY;

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading AI Assist settings…
        </CardContent>
      </Card>
    );
  }

  if (!token) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="p-6 text-sm text-muted-foreground">Sign in to view AI Assist settings.</CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-indigo-400" />
              Platform AI Assist
            </CardTitle>
            <CardDescription>
              Tenant Admins configure provider credentials for PySetu AI features across the control plane.
            </CardDescription>
          </div>
          <Badge variant={settings.available ? "success" : settings.enabled ? "warning" : "secondary"}>
            {settings.available
              ? settings.uses_gateway_fallback
                ? "Active (tenant defaults)"
                : "Active"
              : settings.enabled
                ? isLocalProvider(settings.provider)
                  ? "Endpoint required"
                  : "Key required"
                : "Disabled"}
          </Badge>
        </div>
      </CardHeader>
      <AiAssistFormBody
        key={`${token}-${settings.provider}-${settings.enabled}-${settings.model}-${settings.base_url ?? ""}`}
        settings={settings}
        token={token}
        canEdit={canEdit}
        queryClient={queryClient}
      />
    </Card>
  );
}

function AiAssistFormBody({
  settings,
  token,
  canEdit,
  queryClient,
}: {
  settings: ApiAiAssistSettings;
  token: string;
  canEdit: boolean;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const [enabled, setEnabled] = useState(settings.enabled);
  const [provider, setProvider] = useState(settings.provider);
  const [model, setModel] = useState(settings.model);
  const [baseUrl, setBaseUrl] = useState(settings.base_url ?? DEFAULT_BASE_URLS[settings.provider] ?? "");
  const [apiKey, setApiKey] = useState("");

  const supportedProviders = settings.supported_providers ?? EMPTY.supported_providers ?? [];
  const cloudProviders = supportedProviders.filter((id) => !LOCAL_PROVIDERS.has(id as ApiAiAssistSettings["provider"]));
  const localProviders = supportedProviders.filter((id) => LOCAL_PROVIDERS.has(id as ApiAiAssistSettings["provider"]));

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateAiAssistSettings(token, {
        enabled,
        provider,
        model,
        api_key: apiKey || undefined,
        base_url: isLocalProvider(provider) ? baseUrl : undefined,
      }),
    onSuccess: () => {
      setApiKey("");
      queryClient.invalidateQueries({ queryKey: ["ai-assist-settings"] });
    },
  });

  function clearKey() {
    api.updateAiAssistSettings(token, { api_key: "" }).then(() => {
      queryClient.invalidateQueries({ queryKey: ["ai-assist-settings"] });
    });
  }

  function handleProviderChange(next: ApiAiAssistSettings["provider"]) {
    setProvider(next);
    setModel(defaultModelFor(next));
    setBaseUrl(settings.base_url && isLocalProvider(next) ? settings.base_url : DEFAULT_BASE_URLS[next] ?? "");
  }

  const apiKeyOptional = isLocalProvider(provider);
  const showBaseUrl = isLocalProvider(provider);

  return (
    <CardContent className="space-y-6">
      {settings.air_gap_mode && (
        <p className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
          Air-gap mode is enabled — only local providers (Ollama, vLLM, custom OpenAI-compatible) are available for AI
          Assist.
        </p>
      )}

      <div className="rounded-md border border-border/60 bg-muted/20 p-3 text-xs text-muted-foreground">
        <p className="font-medium text-foreground">Powered features</p>
        <ul className="mt-2 list-inside list-disc space-y-1">
          {(settings.features.length ? settings.features : FEATURE_LIST).map((feature) => (
            <li key={feature}>{feature}</li>
          ))}
        </ul>
        <p className="mt-2">
          Cloud providers (OpenAI, Gemini, Groq) need an API key. Air-gap providers use a local OpenAI-compatible
          endpoint — no outbound cloud call. Tenant default keys below still apply as fallback for OpenAI and Gemini.
        </p>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          disabled={!canEdit}
          className="h-4 w-4 rounded border-input"
        />
        Enable platform AI Assist for this tenant
      </label>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="ai-assist-provider">
            Provider
          </label>
          <select
            id="ai-assist-provider"
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value as ApiAiAssistSettings["provider"])}
            disabled={!canEdit}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
          >
            {cloudProviders.length > 0 && (
              <optgroup label="Cloud">
                {cloudProviders.map((id) => (
                  <option key={id} value={id}>{providerLabel(settings, id)}</option>
                ))}
              </optgroup>
            )}
            {localProviders.length > 0 && (
              <optgroup label="Air-gap / local">
                {localProviders.map((id) => (
                  <option key={id} value={id}>{providerLabel(settings, id)}</option>
                ))}
              </optgroup>
            )}
          </select>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="ai-assist-model">
            Model
          </label>
          <input
            id="ai-assist-model"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={!canEdit}
            placeholder={defaultModelFor(provider)}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
          />
        </div>
      </div>

      {showBaseUrl && (
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="ai-assist-base-url">
            Endpoint base URL
          </label>
          <input
            id="ai-assist-base-url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            disabled={!canEdit}
            placeholder={DEFAULT_BASE_URLS[provider] ?? "http://localhost:8000/v1"}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
          />
          <p className="text-xs text-muted-foreground">
            {provider === "ollama"
              ? "Ollama OpenAI-compatible URL (e.g. http://localhost:11434). Uses tenant Ollama defaults when empty."
              : "OpenAI-compatible chat completions base (e.g. http://host:8000/v1)."}
          </p>
        </div>
      )}

      <div className="space-y-2">
        <label className="text-sm font-medium">
          {apiKeyOptional ? "API key (optional)" : "API key"}
        </label>
        {settings.api_key_set && (
          <p className="text-xs text-muted-foreground">
            Saved: <span className="font-mono">{settings.api_key_masked}</span>
          </p>
        )}
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          disabled={!canEdit}
          placeholder={
            settings.api_key_set
              ? "Enter new key to replace…"
              : provider === "gemini"
                ? "AIza…"
                : provider === "groq"
                  ? "gsk_…"
                  : apiKeyOptional
                    ? "Optional for local endpoints"
                    : "sk-…"
          }
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
        />
        {canEdit && settings.api_key_set && (
          <Button variant="outline" size="sm" onClick={clearKey}>
            Clear saved key
          </Button>
        )}
      </div>

      {canEdit ? (
        <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending} className="gap-2">
          {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save AI Assist Settings
        </Button>
      ) : (
        <p className="text-xs text-muted-foreground">Tenant Admin role required to edit.</p>
      )}
    </CardContent>
  );
}
