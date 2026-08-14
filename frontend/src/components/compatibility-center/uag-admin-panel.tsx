"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ArrowRightLeft, Loader2, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api } from "@/lib/api";
import { useAuthStore, type UserRole } from "@/stores/auth-store";

const UAG_ADMIN_ROLES: UserRole[] = ["tenant_admin", "platform_admin", "security_admin"];

export function UagAdminPanel() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const canManage = Boolean(user?.role && UAG_ADMIN_ROLES.includes(user.role));

  const [requestedModel, setRequestedModel] = useState("gpt-4o");
  const [actualModel, setActualModel] = useState("gemini-1.5-pro");
  const [targetProvider, setTargetProvider] = useState("gemini");
  const [emulateProtocol, setEmulateProtocol] = useState("openai");
  const [clientResponseProtocol, setClientResponseProtocol] = useState("openai");
  const [actionError, setActionError] = useState("");

  const {
    data: mappings = [],
    isLoading: mappingsLoading,
    error: mappingsError,
  } = useQuery({
    queryKey: ["uag-mappings", token],
    queryFn: () => api.listUagMappings(token!),
    enabled: Boolean(token) && canManage,
  });

  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ["uag-settings", token],
    queryFn: () => api.getUagSettings(token!),
    enabled: Boolean(token) && canManage,
  });

  const invalidateMappings = () => queryClient.invalidateQueries({ queryKey: ["uag-mappings"] });
  const invalidateSettings = () => queryClient.invalidateQueries({ queryKey: ["uag-settings"] });

  const createMapping = useMutation({
    mutationFn: () =>
      api.createUagMapping(token!, {
        requested_model: requestedModel,
        actual_model: actualModel,
        target_provider: targetProvider,
        emulate_protocol: emulateProtocol,
      }),
    onSuccess: () => {
      setActionError("");
      invalidateMappings();
    },
    onError: (err) => setActionError(err instanceof ApiError ? err.message : "Unable to create mapping."),
  });

  const deleteMapping = useMutation({
    mutationFn: (id: string) => api.deleteUagMapping(token!, id),
    onSuccess: () => {
      setActionError("");
      invalidateMappings();
    },
    onError: (err) => setActionError(err instanceof ApiError ? err.message : "Unable to delete mapping."),
  });

  const toggleMapping = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.updateUagMapping(token!, id, { enabled }),
    onSuccess: () => {
      setActionError("");
      invalidateMappings();
    },
    onError: (err) => setActionError(err instanceof ApiError ? err.message : "Unable to update mapping."),
  });

  const saveSettings = useMutation({
    mutationFn: () =>
      api.updateUagSettings(token!, {
        client_response_protocol: clientResponseProtocol,
      }),
    onSuccess: () => {
      setActionError("");
      invalidateSettings();
    },
    onError: (err) => setActionError(err instanceof ApiError ? err.message : "Unable to save gateway settings."),
  });

  useEffect(() => {
    if (settings) {
      setClientResponseProtocol(settings.client_response_protocol);
    }
  }, [settings]);

  if (!canManage) {
    return (
      <Card className="border-border/60">
        <CardContent className="p-6 text-sm text-muted-foreground">
          Gateway and model alias configuration requires a tenant admin or security admin role.
        </CardContent>
      </Card>
    );
  }

  const loadError = mappingsError instanceof ApiError ? mappingsError.message : mappingsError ? "Unable to load mappings." : "";

  return (
    <div className="space-y-6">
      {(actionError || loadError) && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {actionError || loadError}
        </div>
      )}

      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="p-4 text-sm text-muted-foreground">
          Condition-based provider routing now lives in{" "}
          <Link href="/llm-router?tab=rules" className="text-primary underline">
            Routing Rules
          </Link>{" "}
          (with optional target provider override). Model aliases are preferred on{" "}
          <Link href="/llm-router?tab=models" className="text-primary underline">
            Model Registry
          </Link>{" "}
          entries. Legacy alias rows below remain supported for per-alias client protocol overrides.
        </CardContent>
      </Card>

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="text-base">Client response format</CardTitle>
          <CardDescription>
            Choose the API shape returned to clients. PySetu routing metadata is omitted by default for strict SDK
            compatibility; append <code className="text-xs">?mode=debug</code> to include it. Per-rule overrides live
            on <Link href="/llm-router?tab=rules" className="text-primary underline">Routing Rules</Link>; client API
            keys can override the tenant default.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {settingsLoading ? (
            <p className="text-sm text-muted-foreground">Loading settings…</p>
          ) : (
            <>
              <div className="grid gap-3 sm:max-w-md">
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">Default client protocol</span>
                  <select
                    value={clientResponseProtocol}
                    onChange={(e) => setClientResponseProtocol(e.target.value)}
                    className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
                  >
                    <option value="openai">OpenAI (chat.completion)</option>
                    <option value="gemini">Gemini (GenerateContent)</option>
                    <option value="anthropic">Anthropic / Claude (Messages)</option>
                  </select>
                </label>
              </div>
              <Button size="sm" disabled={saveSettings.isPending} onClick={() => saveSettings.mutate()}>
                {saveSettings.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save response settings"}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ArrowRightLeft className="h-4 w-4" />
            Legacy model aliases
          </CardTitle>
          <CardDescription>
            Map client model names before routing rules run. Prefer{" "}
            <Link href="/llm-router?tab=models" className="text-primary underline">Model Registry → aliases</Link> for
            new entries. Keep legacy rows when you need a per-alias client protocol override.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <input
              value={requestedModel}
              onChange={(e) => setRequestedModel(e.target.value)}
              placeholder="Requested (gpt-4o)"
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            />
            <input
              value={actualModel}
              onChange={(e) => setActualModel(e.target.value)}
              placeholder="Actual model"
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            />
            <select
              value={targetProvider}
              onChange={(e) => setTargetProvider(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value="gemini">gemini</option>
              <option value="claude">claude</option>
              <option value="ollama">ollama</option>
              <option value="openai">openai</option>
              <option value="azure_openai">azure_openai</option>
            </select>
            <select
              value={emulateProtocol}
              onChange={(e) => setEmulateProtocol(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value="openai">Client: OpenAI</option>
              <option value="gemini">Client: Gemini</option>
              <option value="anthropic">Client: Anthropic</option>
            </select>
          </div>
          <Button size="sm" className="gap-1" disabled={createMapping.isPending} onClick={() => createMapping.mutate()}>
            {createMapping.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Add legacy alias
          </Button>

          {mappingsLoading ? (
            <p className="text-sm text-muted-foreground">Loading aliases…</p>
          ) : mappings.length === 0 ? (
            <p className="rounded-md border border-dashed border-border/60 px-4 py-6 text-center text-sm text-muted-foreground">
              No legacy aliases configured. Add aliases on Model Registry entries instead.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-md border border-border/60">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Requested</th>
                    <th className="px-3 py-2">Actual</th>
                    <th className="px-3 py-2">Provider</th>
                    <th className="px-3 py-2">Client protocol</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {mappings.map((row) => (
                    <tr key={row.id} className="border-t border-border/40">
                      <td className="px-3 py-2 font-medium">{row.requested_model}</td>
                      <td className="px-3 py-2">{row.actual_model}</td>
                      <td className="px-3 py-2">{row.target_provider}</td>
                      <td className="px-3 py-2">{row.emulate_protocol}</td>
                      <td className="px-3 py-2">
                        <label className="flex cursor-pointer items-center gap-2">
                          <input
                            type="checkbox"
                            className="h-4 w-4 rounded border-input"
                            checked={row.enabled}
                            disabled={toggleMapping.isPending}
                            onChange={(e) => toggleMapping.mutate({ id: row.id, enabled: e.target.checked })}
                          />
                          <Badge variant={row.enabled ? "default" : "warning"}>
                            {row.enabled ? "Enabled" : "Disabled"}
                          </Badge>
                        </label>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={deleteMapping.isPending}
                          onClick={() => deleteMapping.mutate(row.id)}
                          title="Delete alias"
                        >
                          <Trash2 className="h-4 w-4 text-red-400" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
