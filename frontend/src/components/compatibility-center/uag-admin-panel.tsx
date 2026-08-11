"use client";

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
  const [policyName, setPolicyName] = useState("Finance to local LLM");
  const [policyConditionKey, setPolicyConditionKey] = useState("department");
  const [policyConditionValue, setPolicyConditionValue] = useState("finance");
  const [policyRouteTo, setPolicyRouteTo] = useState("ollama");
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

  const {
    data: policies = [],
    isLoading: policiesLoading,
    error: policiesError,
  } = useQuery({
    queryKey: ["uag-policies", token],
    queryFn: () => api.listUagPolicies(token!),
    enabled: Boolean(token) && canManage,
  });

  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ["uag-settings", token],
    queryFn: () => api.getUagSettings(token!),
    enabled: Boolean(token) && canManage,
  });

  const invalidateMappings = () => queryClient.invalidateQueries({ queryKey: ["uag-mappings"] });
  const invalidatePolicies = () => queryClient.invalidateQueries({ queryKey: ["uag-policies"] });
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

  const createPolicy = useMutation({
    mutationFn: () =>
      api.createUagPolicy(token!, {
        name: policyName,
        conditions: { [policyConditionKey]: policyConditionValue },
        actions: { route_to: policyRouteTo },
      }),
    onSuccess: () => {
      setActionError("");
      invalidatePolicies();
    },
    onError: (err) => setActionError(err instanceof ApiError ? err.message : "Unable to create policy."),
  });

  const togglePolicy = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.updateUagPolicy(token!, id, { enabled }),
    onSuccess: () => {
      setActionError("");
      invalidatePolicies();
    },
    onError: (err) => setActionError(err instanceof ApiError ? err.message : "Unable to update policy."),
  });

  const deletePolicy = useMutation({
    mutationFn: (id: string) => api.deleteUagPolicy(token!, id),
    onSuccess: () => {
      setActionError("");
      invalidatePolicies();
    },
    onError: (err) => setActionError(err instanceof ApiError ? err.message : "Unable to delete policy."),
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
    onError: (err) => setActionError(err instanceof ApiError ? err.message : "Unable to save UAG settings."),
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
          Universal AI Gateway configuration requires a tenant admin or security admin role.
        </CardContent>
      </Card>
    );
  }

  const loadError =
    (mappingsError instanceof ApiError ? mappingsError.message : mappingsError ? "Unable to load mappings." : "") ||
    (policiesError instanceof ApiError ? policiesError.message : policiesError ? "Unable to load policies." : "");

  return (
    <div className="space-y-6">
      {(actionError || loadError) && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {actionError || loadError}
        </div>
      )}

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="text-base">Client response format</CardTitle>
          <CardDescription>
            Choose the API shape returned to clients. PySetu routing metadata is omitted by default for strict SDK
            compatibility; append <code className="text-xs">?mode=debug</code> to include it. Client API keys can
            override the tenant default. UAG model mappings still override both when a model alias matches.
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
            Provider mappings
          </CardTitle>
          <CardDescription>
            Enable, disable, or delete model aliases. Disabled mappings are ignored at runtime.
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
            Add mapping
          </Button>

          {mappingsLoading ? (
            <p className="text-sm text-muted-foreground">Loading mappings…</p>
          ) : mappings.length === 0 ? (
            <p className="rounded-md border border-dashed border-border/60 px-4 py-6 text-center text-sm text-muted-foreground">
              No provider mappings yet. Add one above or use seed defaults after deployment.
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
                          title="Delete mapping"
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

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="text-base">Provider translation policies</CardTitle>
          <CardDescription>
            Route by department, region, or application. Toggle Active to enable or disable without deleting.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2 md:grid-cols-4">
            <input
              value={policyName}
              onChange={(e) => setPolicyName(e.target.value)}
              placeholder="Policy name"
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            />
            <input
              value={policyConditionKey}
              onChange={(e) => setPolicyConditionKey(e.target.value)}
              placeholder="Condition key"
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            />
            <input
              value={policyConditionValue}
              onChange={(e) => setPolicyConditionValue(e.target.value)}
              placeholder="Condition value"
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            />
            <select
              value={policyRouteTo}
              onChange={(e) => setPolicyRouteTo(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value="ollama">ollama</option>
              <option value="azure_openai">azure_openai</option>
              <option value="gemini">gemini</option>
              <option value="claude">claude</option>
              <option value="openai">openai</option>
            </select>
          </div>
          <Button size="sm" disabled={createPolicy.isPending} onClick={() => createPolicy.mutate()}>
            {createPolicy.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add translation policy"}
          </Button>

          {policiesLoading ? (
            <p className="text-sm text-muted-foreground">Loading policies…</p>
          ) : policies.length === 0 ? (
            <p className="rounded-md border border-dashed border-border/60 px-4 py-6 text-center text-sm text-muted-foreground">
              No translation policies configured yet.
            </p>
          ) : (
            <div className="space-y-2">
              {policies.map((policy) => (
                <div key={policy.id} className="rounded-md border border-border/60 p-3 text-sm">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{policy.name}</span>
                        <Badge variant="outline">priority {policy.priority}</Badge>
                        <Badge variant={policy.enabled ? "default" : "warning"}>
                          {policy.enabled ? "Enabled" : "Disabled"}
                        </Badge>
                      </div>
                      <p className="mt-1 font-mono text-xs text-muted-foreground">
                        IF {JSON.stringify(policy.conditions)} THEN {JSON.stringify(policy.actions)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-input"
                          checked={policy.enabled}
                          disabled={togglePolicy.isPending}
                          onChange={(e) => togglePolicy.mutate({ id: policy.id, enabled: e.target.checked })}
                        />
                        Active
                      </label>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={deletePolicy.isPending}
                        onClick={() => deletePolicy.mutate(policy.id)}
                        title="Delete policy"
                      >
                        <Trash2 className="h-4 w-4 text-red-400" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
