"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Loader2, Save } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiIntegrationSettings } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const EMPTY_INTEGRATIONS: ApiIntegrationSettings = {
  openai_api_key_set: false,
  openai_api_key_masked: null,
  gemini_api_key_set: false,
  gemini_api_key_masked: null,
  gemini_default_model: "gemini-1.5-pro",
  ollama_enabled: false,
  ollama_base_url: "http://localhost:11434",
  ollama_default_model: "llama3.2",
  active_upstream: "none",
  streaming_enabled: true,
  config_source: "environment",
  secrets_backend: "database",
  vault_auth_method: null,
  env_fallback_note:
    "Environment variables (.env / Docker) are used when tenant settings are empty. Tenant settings in this page take priority.",
};

export function IntegrationsSettings() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";

  const { data, isLoading } = useQuery({
    queryKey: ["integrations", token],
    queryFn: () => api.getIntegrations(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const settings = data ?? EMPTY_INTEGRATIONS;

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading integrations…
        </CardContent>
      </Card>
    );
  }

  if (!token) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="p-6 text-sm text-muted-foreground">Sign in to view integration settings.</CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" />
              AI Provider Integrations
            </CardTitle>
            <CardDescription>
              Configure API keys per tenant. Settings here override Docker / .env defaults.
            </CardDescription>
          </div>
          <Badge variant={settings.active_upstream === "mock" ? "warning" : "success"}>
            Active: {settings.active_upstream}
          </Badge>
        </div>
      </CardHeader>
      <IntegrationsFormBody
        key={`${token}-${settings.config_source}-${settings.gemini_default_model}-${settings.ollama_enabled}`}
        settings={settings}
        token={token}
        canEdit={canEdit}
        queryClient={queryClient}
      />
    </Card>
  );
}

function IntegrationsFormBody({
  settings,
  token,
  canEdit,
  queryClient,
}: {
  settings: ApiIntegrationSettings;
  token: string | null;
  canEdit: boolean;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const [openaiKey, setOpenaiKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState(settings.gemini_default_model);
  const [ollamaEnabled, setOllamaEnabled] = useState(settings.ollama_enabled);
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState(settings.ollama_base_url);
  const [ollamaModel, setOllamaModel] = useState(settings.ollama_default_model);

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateIntegrations(token!, {
        openai_api_key: openaiKey || undefined,
        gemini_api_key: geminiKey || undefined,
        gemini_default_model: geminiModel,
        ollama_enabled: ollamaEnabled,
        ollama_base_url: ollamaBaseUrl,
        ollama_default_model: ollamaModel,
      }),
    onSuccess: () => {
      setOpenaiKey("");
      setGeminiKey("");
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      queryClient.invalidateQueries({ queryKey: ["gateway-status"] });
      queryClient.invalidateQueries({ queryKey: ["ollama-status"] });
    },
  });

  function clearOpenAiKey() {
    if (!token) return;
    api.updateIntegrations(token, { openai_api_key: "" }).then(() => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
    });
  }

  return (
    <CardContent className="space-y-6">
      <p className="rounded-md border border-border/60 bg-muted/20 p-3 text-xs text-muted-foreground">
        {settings.env_fallback_note} Current source: <strong>{settings.config_source}</strong>. Secrets backend:{" "}
        <strong>{settings.secrets_backend}</strong>
        {settings.secrets_backend === "vault" && (
          <>
            {" "}
            (API keys stored in Hashicorp Vault, not in the database
            {settings.vault_auth_method ? `; auth: ${settings.vault_auth_method}` : ""}).
          </>
        )}
      </p>

      <div className="space-y-2">
        <label className="text-sm font-medium">OpenAI API Key</label>
        {settings.openai_api_key_set && (
          <p className="text-xs text-muted-foreground">
            Saved: <span className="font-mono">{settings.openai_api_key_masked}</span>
          </p>
        )}
        <input
          type="password"
          value={openaiKey}
          onChange={(e) => setOpenaiKey(e.target.value)}
          disabled={!canEdit}
          placeholder={settings.openai_api_key_set ? "Enter new key to replace…" : "sk-…"}
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
        />
        {canEdit && settings.openai_api_key_set && (
          <Button variant="outline" size="sm" onClick={clearOpenAiKey}>
            Clear saved key
          </Button>
        )}
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Google Gemini API Key</label>
        {settings.gemini_api_key_set && (
          <p className="text-xs text-muted-foreground">
            Saved: <span className="font-mono">{settings.gemini_api_key_masked}</span>
          </p>
        )}
        <input
          type="password"
          value={geminiKey}
          onChange={(e) => setGeminiKey(e.target.value)}
          disabled={!canEdit}
          placeholder={settings.gemini_api_key_set ? "Enter new key to replace…" : "AIza…"}
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
        />
        <input
          value={geminiModel}
          onChange={(e) => setGeminiModel(e.target.value)}
          disabled={!canEdit}
          placeholder="gemini-1.5-pro"
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
        />
        <p className="text-xs text-muted-foreground">
          Priority: OpenAI → Gemini → Ollama. Use model name containing &quot;gemini&quot; to force Gemini routing.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium">
            <input
              type="checkbox"
              checked={ollamaEnabled}
              onChange={(e) => setOllamaEnabled(e.target.checked)}
              disabled={!canEdit}
              className="rounded border-input"
            />
            Enable Ollama
          </label>
          <p className="text-xs text-muted-foreground">
            Use local Ollama when no OpenAI key is set (OpenAI takes priority).
          </p>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Ollama Base URL</label>
          <input
            value={ollamaBaseUrl}
            onChange={(e) => setOllamaBaseUrl(e.target.value)}
            disabled={!canEdit}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
          />
        </div>
        <div className="space-y-2 sm:col-span-2">
          <label className="text-sm font-medium">Default Ollama Model</label>
          <input
            value={ollamaModel}
            onChange={(e) => setOllamaModel(e.target.value)}
            disabled={!canEdit}
            placeholder="llama3.2"
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
          />
        </div>
      </div>

      {canEdit ? (
        <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending} className="gap-2">
          {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save Integrations
        </Button>
      ) : (
        <p className="text-xs text-muted-foreground">Tenant Admin or Security Admin role required to edit.</p>
      )}
    </CardContent>
  );
}