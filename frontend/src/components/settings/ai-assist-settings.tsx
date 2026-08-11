"use client";

import { useState } from "react";
import Link from "next/link";
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
];

const EMPTY: ApiAiAssistSettings = {
  enabled: false,
  provider: "openai",
  model: "gpt-4o-mini",
  api_key_set: false,
  api_key_masked: null,
  available: false,
  features: [],
  air_gap_mode: false,
};

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
              Tenant Admins configure one API key for HelixGuard AI features across the control plane.
            </CardDescription>
          </div>
          <Badge variant={settings.available ? "success" : settings.enabled ? "warning" : "secondary"}>
            {settings.available ? "Active" : settings.enabled ? "Key required" : "Disabled"}
          </Badge>
        </div>
      </CardHeader>
      <AiAssistFormBody
        key={`${token}-${settings.provider}-${settings.enabled}-${settings.model}`}
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
  const [apiKey, setApiKey] = useState("");

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateAiAssistSettings(token, {
        enabled,
        provider,
        model,
        api_key: apiKey || undefined,
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

  return (
    <CardContent className="space-y-6">
      {settings.air_gap_mode && (
        <p className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
          Air-gap mode is enabled — external AI Assist providers are disabled for this deployment.
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
          Gateway traffic uses <Link href="/settings/integrations" className="text-primary underline">Integrations</Link>{" "}
          keys. AI Assist is separate and only used for in-product guidance and analysis.
        </p>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          disabled={!canEdit || settings.air_gap_mode}
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
            onChange={(e) => {
              const next = e.target.value as ApiAiAssistSettings["provider"];
              setProvider(next);
              if (next === "gemini" && model.startsWith("gpt")) setModel("gemini-1.5-flash");
              if (next === "openai" && model.startsWith("gemini")) setModel("gpt-4o-mini");
            }}
            disabled={!canEdit}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
          >
            <option value="openai">OpenAI</option>
            <option value="gemini">Google Gemini</option>
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
            placeholder={provider === "gemini" ? "gemini-1.5-flash" : "gpt-4o-mini"}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">AI Assist API Key</label>
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
          placeholder={settings.api_key_set ? "Enter new key to replace…" : provider === "gemini" ? "AIza…" : "sk-…"}
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
