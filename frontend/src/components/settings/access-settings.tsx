"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, Layers, Loader2, Plus, Trash2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  api,
  type ApiClientApiKey,
  type ApiClientApiKeyCreateResponse,
  type ApiPolicyBundle,
  type ApiPolicyTreeNode,
} from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

function flattenPolicies(nodes: ApiPolicyTreeNode[]): ApiPolicyTreeNode[] {
  const out: ApiPolicyTreeNode[] = [];
  for (const node of nodes) {
    if (node.type === "policy") out.push(node);
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
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyBundleId, setNewKeyBundleId] = useState("");
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

  const policies = useMemo(() => flattenPolicies(policyTree), [policyTree]);

  const createBundle = useMutation({
    mutationFn: () =>
      api.createPolicyBundle(token!, {
        name: newBundleName,
        description: newBundleDesc,
        policy_ids: newBundlePolicyIds,
        is_default: bundles.length === 0,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-bundles"] });
      setNewBundleName("");
      setNewBundleDesc("");
      setNewBundlePolicyIds([]);
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
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["client-api-keys"] });
      setCreatedKey(data);
      setNewKeyName("");
      setNewKeyBundleId("");
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
                    {bundle.policy_ids.length === 0 && (
                      <span className="text-xs text-muted-foreground">No policies attached</span>
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
                      {p.label}
                    </label>
                  ))}
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
            <code className="text-xs">Authorization: Bearer hg_…</code> instead of a JWT.
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
              </div>
              {canEdit && (
                <div className="flex gap-2">
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
