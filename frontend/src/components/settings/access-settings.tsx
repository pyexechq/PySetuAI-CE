"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, Layers, Loader2, Plus, Trash2, Folder } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiKeyLimitsForm } from "./api-key-limits";
import {
  api,
  type ApiClientApiKey,
  type ApiClientApiKeyCreateResponse,
  type ApiPolicyBundle,
  type ApiPolicyTreeNode,
  customIntentsAPI,
} from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const CLIENT_PROTOCOL_OPTIONS = [
  { value: "", label: "Inherit tenant default" },
  { value: "openai", label: "OpenAI (chat.completion)" },
  { value: "gemini", label: "Gemini (GenerateContent)" },
  { value: "anthropic", label: "Anthropic / Claude (Messages)" },
] as const;

function protocolLabel(value: string | null | undefined) {
  return CLIENT_PROTOCOL_OPTIONS.find((option) => option.value === (value ?? ""))?.label ?? "Inherit tenant default";
}

function flattenPolicies(nodes: ApiPolicyTreeNode[]): ApiPolicyTreeNode[] {
  const out: ApiPolicyTreeNode[] = [];
  for (const node of nodes) {
    if (node.type === "policy" || node.type === "folder") out.push(node);
    if (node.children?.length) out.push(...flattenPolicies(node.children));
  }
  return out;
}

export type AccessSettingsSection = "bundles" | "keys" | "all";

export function AccessSettings({ section = "all" }: { section?: AccessSettingsSection }) {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";

  const [newBundleName, setNewBundleName] = useState("");
  const [newBundleDesc, setNewBundleDesc] = useState("");
  const [newBundlePolicyIds, setNewBundlePolicyIds] = useState<string[]>([]);
  const [newBundleCustomIntentIds, setNewBundleCustomIntentIds] = useState<string[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyBundleId, setNewKeyBundleId] = useState("");
  const [newKeyClientProtocol, setNewKeyClientProtocol] = useState("");
  const [newKeyLimits, setNewKeyLimits] = useState({
    ai_rate_limit_rpm: null as number | null,
    ai_rate_limit_rph: null as number | null,
    ai_rate_limit_rpd: null as number | null,
    ai_token_limit_tpm: null as number | null,
    ai_token_limit_tph: null as number | null,
    ai_token_limit_tpd: null as number | null,
  });
  const [editingKeyLimits, setEditingKeyLimits] = useState<ApiClientApiKey | null>(null);
  const [createdKey, setCreatedKey] = useState<ApiClientApiKeyCreateResponse | null>(null);

  const { data: bundles = [], isLoading: bundlesLoading } = useQuery({
    queryKey: ["policy-bundles", token],
    queryFn: () => api.getPolicyBundles(token!),
    enabled: Boolean(token),
  });

  const { data: keys = [], isLoading: keysLoading } = useQuery({
    queryKey: ["client-api-keys", token],
    queryFn: () => api.getClientApiKeys(token!),
    enabled: Boolean(token),
  });

  const { data: policyTree = [] } = useQuery({
    queryKey: ["policy-tree", token],
    queryFn: () => api.getPolicyTree(token!),
    enabled: Boolean(token),
  });
  
  const { data: customIntents = [] } = useQuery({
    queryKey: ["custom-intents", token],
    queryFn: () => customIntentsAPI.list(token!),
    enabled: Boolean(token),
  });

  const policies = useMemo(() => flattenPolicies(policyTree), [policyTree]);

  const createBundle = useMutation({
    mutationFn: () =>
      api.createPolicyBundle(token!, {
        name: newBundleName,
        description: newBundleDesc,
        policy_ids: newBundlePolicyIds,
        custom_intent_ids: newBundleCustomIntentIds,
        is_default: bundles.length === 0,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-bundles"] });
      setNewBundleName("");
      setNewBundleDesc("");
      setNewBundlePolicyIds([]);
      setNewBundleCustomIntentIds([]);
    },
  });

  const deleteBundle = useMutation({
    mutationFn: (id: string) => api.deletePolicyBundle(token!, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["policy-bundles"] }),
  });

  const createKey = useMutation({
    mutationFn: () =>
      api.createClientApiKey(token!, {
        name: newKeyName,
        bundle_id: newKeyBundleId || undefined,
        client_response_protocol: newKeyClientProtocol || null,
        ...newKeyLimits,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["client-api-keys"] });
      setCreatedKey(data);
      setNewKeyName("");
      setNewKeyBundleId("");
      setNewKeyClientProtocol("");
      setNewKeyLimits({
        ai_rate_limit_rpm: null,
        ai_rate_limit_rph: null,
        ai_rate_limit_rpd: null,
        ai_token_limit_tpm: null,
        ai_token_limit_tph: null,
        ai_token_limit_tpd: null,
      });
    },
  });

  const updateKeyProtocol = useMutation({
    mutationFn: ({ id, client_response_protocol }: { id: string; client_response_protocol: string | null }) =>
      api.updateClientApiKey(token!, id, { client_response_protocol }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["client-api-keys"] }),
  });

  const updateKeyLimits = useMutation({
    mutationFn: (updates: Partial<ApiClientApiKey> & { id: string }) => {
      const { id, ...rest } = updates;
      return api.updateClientApiKey(token!, id, rest);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client-api-keys"] });
      setEditingKeyLimits(null);
    },
  });

  const toggleKey = useMutation({
    mutationFn: (key: ApiClientApiKey) =>
      api.updateClientApiKey(token!, key.id, { is_active: !key.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["client-api-keys"] }),
  });

  const deleteKey = useMutation({
    mutationFn: (id: string) => api.deleteClientApiKey(token!, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["client-api-keys"] }),
  });

  if (!token) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="p-6 text-sm text-muted-foreground">Sign in to manage access settings.</CardContent>
      </Card>
    );
  }

  if (bundlesLoading || keysLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading access settings…
        </CardContent>
      </Card>
    );
  }

  const showBundles = section === "all" || section === "bundles";
  const showKeys = section === "all" || section === "keys";

  return (
    <div className="space-y-6">
      {showBundles && (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5" />
            Policy Bundles
          </CardTitle>
          <CardDescription>
            Group policies by use case. Client API keys attach to a bundle; JWT gateway calls use the tenant default
            bundle.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {bundles.map((bundle: ApiPolicyBundle) => (
            <div key={bundle.id} className="rounded-lg border border-border/60 p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{bundle.name}</p>
                    {bundle.is_default && <Badge variant="secondary">Default</Badge>}
                    <Badge variant="outline">{bundle.status}</Badge>
                  </div>
                  {bundle.description && <p className="mt-1 text-sm text-muted-foreground">{bundle.description}</p>}
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(bundle.policy_names.length ? bundle.policy_names : bundle.policy_ids).map((label, i) => (
                      <Badge key={`${bundle.id}-${i}`} variant="outline" className="text-xs">
                        {label}
                      </Badge>
                    ))}
                    {(bundle.custom_intent_ids || []).map((id, i) => {
                      const intent = customIntents.find((ci) => ci.id === id);
                      return (
                        <Badge key={`intent-${bundle.id}-${i}`} variant="outline" className="text-xs border-purple-500/30 text-purple-600 dark:text-purple-400">
                          {intent ? intent.name : id}
                        </Badge>
                      );
                    })}
                    {bundle.policy_ids.length === 0 && (bundle.custom_intent_ids || []).length === 0 && (
                      <span className="text-xs text-muted-foreground">No policies or intents attached</span>
                    )}
                  </div>
                </div>
                {canEdit && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => deleteBundle.mutate(bundle.id)}
                    disabled={deleteBundle.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          ))}

          {canEdit && (
            <div className="space-y-3 rounded-lg border border-dashed border-border/60 p-4">
              <p className="text-sm font-medium">New bundle</p>
              <input
                value={newBundleName}
                onChange={(e) => setNewBundleName(e.target.value)}
                placeholder="Bundle name"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              />
              <input
                value={newBundleDesc}
                onChange={(e) => setNewBundleDesc(e.target.value)}
                placeholder="Description (optional)"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              />
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Attach policies (order matters)</p>
                <div className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-input p-2">
                  {policies.map((p) => (
                    <label key={p.id} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={newBundlePolicyIds.includes(p.id)}
                        onChange={(e) => {
                          if (e.target.checked) setNewBundlePolicyIds((ids) => [...ids, p.id]);
                          else setNewBundlePolicyIds((ids) => ids.filter((id) => id !== p.id));
                        }}
                      />
                      {p.type === "folder" ? <Folder className="h-4 w-4 text-muted-foreground" /> : null}
                      {p.label}
                    </label>
                  ))}
                  {policies.length === 0 && <span className="text-xs text-muted-foreground">No policies available</span>}
                </div>
              </div>
              
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Attach Custom Intents</p>
                <div className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-input p-2">
                  {customIntents.map((intent) => (
                    <label key={intent.id} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={newBundleCustomIntentIds.includes(intent.id)}
                        onChange={(e) => {
                          if (e.target.checked) setNewBundleCustomIntentIds((ids) => [...ids, intent.id]);
                          else setNewBundleCustomIntentIds((ids) => ids.filter((id) => id !== intent.id));
                        }}
                      />
                      {intent.intent_type === "folder" ? <Folder className="h-4 w-4 text-muted-foreground" /> : null}
                      {intent.name}
                    </label>
                  ))}
                  {customIntents.length === 0 && <span className="text-xs text-muted-foreground">No custom intents available</span>}
                </div>
              </div>
              <Button
                size="sm"
                className="gap-2"
                disabled={!newBundleName.trim() || createBundle.isPending}
                onClick={() => createBundle.mutate()}
              >
                {createBundle.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Create bundle
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
      )}

      {showKeys && (
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5" />
            Client API Keys
          </CardTitle>
          <CardDescription>
            Ingress keys for applications calling <code className="text-xs">/v1/chat/completions</code>. Use{" "}
            <code className="text-xs">Authorization: Bearer hg_…</code> instead of a JWT. Each key can set its own
            client response format (OpenAI, Gemini, or Anthropic) or inherit the tenant UAG default.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {createdKey && (
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm">
              <p className="font-medium text-emerald-300">Key created — copy now (shown once)</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <code className="rounded bg-black/30 px-2 py-1 font-mono text-xs">{createdKey.api_key}</code>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={() => navigator.clipboard.writeText(createdKey.api_key)}
                >
                  <Copy className="h-3 w-3" />
                  Copy
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setCreatedKey(null)}>
                  Dismiss
                </Button>
              </div>
            </div>
          )}

          {keys.map((key: ApiClientApiKey) => (
            <div key={key.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/60 p-4">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium">{key.name}</p>
                  <Badge variant={key.is_active ? "success" : "secondary"}>
                    {key.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
                <p className="font-mono text-xs text-muted-foreground">{key.key_masked}</p>
                {key.bundle_name && (
                  <p className="mt-1 text-xs text-muted-foreground">Bundle: {key.bundle_name}</p>
                )}
                <p className="mt-1 text-xs text-muted-foreground">
                  Response format: {protocolLabel(key.client_response_protocol)}
                </p>
                <div className="mt-2 text-xs text-muted-foreground">
                  Limits: {key.ai_rate_limit_rpm || '∞'} RPM / {key.ai_token_limit_tpm || '∞'} TPM
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                {canEdit && (
                  <div className="flex flex-wrap items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => setEditingKeyLimits(key)}>
                      Edit Limits
                    </Button>
                    <select
                      value={key.client_response_protocol ?? ""}
                      disabled={updateKeyProtocol.isPending}
                      onChange={(e) =>
                        updateKeyProtocol.mutate({
                          id: key.id,
                          client_response_protocol: e.target.value || null,
                        })
                      }
                      className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                      title="Client response format"
                    >
                      {CLIENT_PROTOCOL_OPTIONS.map((option) => (
                        <option key={option.value || "inherit"} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <Button variant="outline" size="sm" onClick={() => toggleKey.mutate(key)}>
                      {key.is_active ? "Deactivate" : "Activate"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => deleteKey.mutate(key.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
                {editingKeyLimits?.id === key.id && (
                  <div className="w-full mt-2 rounded-lg border border-border/60 bg-muted/20 p-3 max-w-[400px]">
                    <ApiKeyLimitsForm 
                      limits={editingKeyLimits}
                      onChange={(field, value) => setEditingKeyLimits(prev => prev ? ({ ...prev, [field]: value } as ApiClientApiKey) : null)}
                      disabled={updateKeyLimits.isPending}
                    />
                    <div className="mt-3 flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setEditingKeyLimits(null)}>
                        Cancel
                      </Button>
                      <Button size="sm" onClick={() => updateKeyLimits.mutate(editingKeyLimits)} disabled={updateKeyLimits.isPending}>
                        {updateKeyLimits.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {canEdit && (
            <div className="space-y-3 rounded-lg border border-dashed border-border/60 p-4">
              <p className="text-sm font-medium">New client API key</p>
              <input
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="Key name (e.g. support-agent)"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              />
              <select
                value={newKeyBundleId}
                onChange={(e) => setNewKeyBundleId(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="">No bundle (builtin rules only)</option>
                {bundles.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
              <select
                value={newKeyClientProtocol}
                onChange={(e) => setNewKeyClientProtocol(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                {CLIENT_PROTOCOL_OPTIONS.map((option) => (
                  <option key={option.value || "inherit"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              
              <ApiKeyLimitsForm 
                limits={newKeyLimits}
                onChange={(field, value) => setNewKeyLimits(prev => ({ ...prev, [field]: value }))}
                disabled={createKey.isPending}
              />

              <Button
                size="sm"
                className="gap-2"
                disabled={!newKeyName.trim() || createKey.isPending}
                onClick={() => createKey.mutate()}
              >
                {createKey.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Generate key
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
      )}
    </div>
  );
}
