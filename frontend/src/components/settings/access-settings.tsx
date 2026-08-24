"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Copy, Eye, Globe2, KeyRound, Layers, Loader2, Pencil, Plus, Search, ShieldCheck, Trash2, Folder, X } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AppModal } from "@/components/ui/dialog";
import { ApiKeyLimitsForm } from "./api-key-limits";
import {
  ApiKeyOriginsForm,
  originsLabel,
  originsModeFromKey,
  originsToPayload,
  type ApiKeyOriginsMode,
} from "./api-key-origins";
import {
  api,
  type ApiClientApiKey,
  type ApiClientApiKeyCreateResponse,
  type ApiClientApiKeyRevealResponse,
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
  const [newBundleFrameworkPacks, setNewBundleFrameworkPacks] = useState<string[]>([]);
  const [newBundleMcpMode, setNewBundleMcpMode] = useState<"all" | "allowlist" | "denylist">("allowlist");
  const [newBundleMcpEntries, setNewBundleMcpEntries] = useState<{ server_id: string; tool_names: string[] }[]>([]);

  const [editingBundleId, setEditingBundleId] = useState<string | null>(null);
  const [editBundleName, setEditBundleName] = useState("");
  const [editBundleDesc, setEditBundleDesc] = useState("");
  const [editBundlePolicyIds, setEditBundlePolicyIds] = useState<string[]>([]);
  const [editBundleCustomIntentIds, setEditBundleCustomIntentIds] = useState<string[]>([]);
  const [editBundleFrameworkPacks, setEditBundleFrameworkPacks] = useState<string[]>([]);
  const [editBundleMcpMode, setEditBundleMcpMode] = useState<"all" | "allowlist" | "denylist">("allowlist");
  const [editBundleMcpEntries, setEditBundleMcpEntries] = useState<{ server_id: string; tool_names: string[] }[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyType, setNewKeyType] = useState<"pysetu" | "mirrored">("pysetu");
  const [newMirroredKey, setNewMirroredKey] = useState("");
  const [newKeyPassThrough, setNewKeyPassThrough] = useState(true);
  const [newKeyBundleId, setNewKeyBundleId] = useState("");
  const [newKeyClientProtocol, setNewKeyClientProtocol] = useState("");
  const [newKeyOriginsMode, setNewKeyOriginsMode] = useState<ApiKeyOriginsMode>("inherit");
  const [newKeyOriginsText, setNewKeyOriginsText] = useState("");
  const [newKeyLimits, setNewKeyLimits] = useState({
    ai_rate_limit_rpm: null as number | null,
    ai_rate_limit_rph: null as number | null,
    ai_rate_limit_rpd: null as number | null,
    ai_token_limit_tpm: null as number | null,
    ai_token_limit_tph: null as number | null,
    ai_token_limit_tpd: null as number | null,
    token_saving_enabled: null as boolean | null,
    token_saving_mode: null as string | null,
  });
  const [editingKeyLimits, setEditingKeyLimits] = useState<ApiClientApiKey | null>(null);
  const [createdKey, setCreatedKey] = useState<ApiClientApiKeyCreateResponse | null>(null);
  const [revealedKey, setRevealedKey] = useState<ApiClientApiKeyRevealResponse | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [keySearch, setKeySearch] = useState("");
  const [keyFilter, setKeyFilter] = useState<"all" | "active" | "inactive">("all");
  const [showCreateKey, setShowCreateKey] = useState(false);

  const { data: bundles = [], isLoading: bundlesLoading } = useQuery({
    queryKey: ["policy-bundles", token],
    queryFn: () => api.getPolicyBundles(token!),
    enabled: Boolean(token),
  });

  const { data: frameworkPacks = [] } = useQuery({
    queryKey: ["framework-rule-packs", token],
    queryFn: () => api.getFrameworkRulePacks(token!),
    enabled: Boolean(token),
  });

  const { data: mcpServers = [] } = useQuery({
    queryKey: ["mcp-servers", token],
    queryFn: () => api.getMcpServers(token!),
    enabled: Boolean(token),
  });

  const { data: keys = [], isLoading: keysLoading } = useQuery({
    queryKey: ["client-api-keys", token],
    queryFn: () => api.getClientApiKeys(token!),
    enabled: Boolean(token),
  });

  const { data: gatewaySettings } = useQuery({
    queryKey: ["gateway-settings", token],
    queryFn: () => api.getGatewaySettings(token!),
    enabled: Boolean(token),
  });

  const tenantOriginCount = gatewaySettings?.allowed_api_origins?.length ?? 0;

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
        framework_rule_packs: newBundleFrameworkPacks,
        mcp_scope: {
          mode: newBundleMcpMode,
          entries: newBundleMcpEntries.filter((entry) => entry.server_id),
        },
        is_default: bundles.length === 0,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-bundles"] });
      setNewBundleName("");
      setNewBundleDesc("");
      setNewBundlePolicyIds([]);
      setNewBundleCustomIntentIds([]);
      setNewBundleFrameworkPacks([]);
      setNewBundleMcpMode("allowlist");
      setNewBundleMcpEntries([]);
    },
  });

  const deleteBundle = useMutation({
    mutationFn: (id: string) => api.deletePolicyBundle(token!, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["policy-bundles"] }),
  });

  const updateBundle = useMutation({
    mutationFn: () =>
      api.updatePolicyBundle(token!, editingBundleId!, {
        name: editBundleName,
        description: editBundleDesc,
        policy_ids: editBundlePolicyIds,
        custom_intent_ids: editBundleCustomIntentIds,
        framework_rule_packs: editBundleFrameworkPacks,
        mcp_scope: {
          mode: editBundleMcpMode,
          entries: editBundleMcpEntries.filter((entry) => entry.server_id),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-bundles"] });
      setEditingBundleId(null);
    },
  });

  const createKey = useMutation({
    mutationFn: () => {
      const allowed_api_origins = originsToPayload(newKeyOriginsMode, newKeyOriginsText);
      if (newKeyType === "mirrored") {
        return api.createMirroredClientApiKey(token!, {
          name: newKeyName,
          mirrored_api_key: newMirroredKey,
          bundle_id: newKeyBundleId || undefined,
          client_response_protocol: newKeyClientProtocol || null,
          upstream_pass_through: newKeyPassThrough,
          allowed_api_origins,
          ...newKeyLimits,
        });
      }
      return api.createClientApiKey(token!, {
        name: newKeyName,
        bundle_id: newKeyBundleId || undefined,
        client_response_protocol: newKeyClientProtocol || null,
        allowed_api_origins,
        ...newKeyLimits,
      });
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["client-api-keys"] });
      if ("api_key" in data && data.api_key) {
        setCreatedKey(data as ApiClientApiKeyCreateResponse);
      }
      setNewKeyName("");
      setNewKeyType("pysetu");
      setNewMirroredKey("");
      setNewKeyPassThrough(true);
      setNewKeyBundleId("");
      setNewKeyClientProtocol("");
      setNewKeyOriginsMode("inherit");
      setNewKeyOriginsText("");
      setNewKeyLimits({
        ai_rate_limit_rpm: null,
        ai_rate_limit_rph: null,
        ai_rate_limit_rpd: null,
        ai_token_limit_tpm: null,
        ai_token_limit_tph: null,
        ai_token_limit_tpd: null,
        token_saving_enabled: null,
        token_saving_mode: null,
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

  const revealKey = useMutation({
    mutationFn: (id: string) => api.revealClientApiKey(token!, id),
    onSuccess: (data) => {
      setRevealedKey(data);
      setCopiedKey(false);
    },
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
  const activeKeyCount = keys.filter((key) => key.is_active).length;
  const browserKeyCount = keys.filter((key) =>
    (key.allowed_api_origins || []).some((origin) => origin.startsWith("chrome-extension://") || origin.startsWith("edge-extension://"))
  ).length;
  const filteredKeys = keys.filter((key) => {
    const search = keySearch.trim().toLowerCase();
    const matchesSearch = !search || [key.name, key.key_masked, key.bundle_name, key.key_source].some((value) => value?.toLowerCase().includes(search));
    const matchesFilter = keyFilter === "all" || (keyFilter === "active" ? key.is_active : !key.is_active);
    return matchesSearch && matchesFilter;
  });

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
                    {(bundle.framework_rule_packs || []).map((packId, i) => {
                      const pack = frameworkPacks.find((p) => p.id === packId);
                      return (
                        <Badge key={`pack-${bundle.id}-${i}`} variant="outline" className="text-xs border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
                          {pack ? pack.name : packId}
                        </Badge>
                      );
                    })}
                    {bundle.mcp_scope && (
                      <Badge variant="outline" className="text-xs border-sky-500/30 text-sky-600 dark:text-sky-400">
                        MCP scope: {bundle.mcp_scope.mode}
                        {bundle.mcp_scope.entries.length > 0 ? ` · ${bundle.mcp_scope.entries.length} server${bundle.mcp_scope.entries.length > 1 ? "s" : ""}` : ""}
                      </Badge>
                    )}
                    {bundle.policy_ids.length === 0 && (bundle.custom_intent_ids || []).length === 0 && (bundle.framework_rule_packs || []).length === 0 && !bundle.mcp_scope && (
                      <span className="text-xs text-muted-foreground">No policies, intents, or rule packs attached</span>
                    )}
                  </div>
                </div>
                {canEdit && (
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setEditingBundleId(bundle.id);
                        setEditBundleName(bundle.name);
                        setEditBundleDesc(bundle.description || "");
                        setEditBundlePolicyIds(bundle.policy_ids || []);
                        setEditBundleCustomIntentIds(bundle.custom_intent_ids || []);
                        setEditBundleFrameworkPacks(bundle.framework_rule_packs || []);
                        setEditBundleMcpMode(bundle.mcp_scope?.mode || "allowlist");
                        setEditBundleMcpEntries(bundle.mcp_scope?.entries || []);
                      }}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => deleteBundle.mutate(bundle.id)}
                      disabled={deleteBundle.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>

              {editingBundleId === bundle.id && (
                <div className="space-y-3 mt-4 pt-4 border-t border-border/60">
                  <p className="text-sm font-medium">Edit bundle</p>
                  <input
                    value={editBundleName}
                    onChange={(e) => setEditBundleName(e.target.value)}
                    placeholder="Bundle name"
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  />
                  <input
                    value={editBundleDesc}
                    onChange={(e) => setEditBundleDesc(e.target.value)}
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
                            checked={editBundlePolicyIds.includes(p.id)}
                            onChange={(e) => {
                              if (e.target.checked) setEditBundlePolicyIds((ids) => [...ids, p.id]);
                              else setEditBundlePolicyIds((ids) => ids.filter((id) => id !== p.id));
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
                            checked={editBundleCustomIntentIds.includes(intent.id)}
                            onChange={(e) => {
                              if (e.target.checked) setEditBundleCustomIntentIds((ids) => [...ids, intent.id]);
                              else setEditBundleCustomIntentIds((ids) => ids.filter((id) => id !== intent.id));
                            }}
                          />
                          {intent.intent_type === "folder" ? <Folder className="h-4 w-4 text-muted-foreground" /> : null}
                          {intent.name}
                        </label>
                      ))}
                      {customIntents.length === 0 && <span className="text-xs text-muted-foreground">No custom intents available</span>}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground">Framework rule packs</p>
                    <div className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-input p-2">
                      {frameworkPacks.map((pack) => (
                        <label key={pack.id} className="flex items-start gap-2 text-sm">
                          <input
                            type="checkbox"
                            className="mt-0.5"
                            checked={editBundleFrameworkPacks.includes(pack.id)}
                            onChange={(e) => {
                              if (e.target.checked) setEditBundleFrameworkPacks((ids) => [...ids, pack.id]);
                              else setEditBundleFrameworkPacks((ids) => ids.filter((id) => id !== pack.id));
                            }}
                          />
                          <span>
                            <span className="font-medium">{pack.name}</span>
                            <span className="ml-1 text-xs text-muted-foreground">v{pack.version} · {pack.rule_count} rules</span>
                            <span className="block text-xs text-muted-foreground">{pack.description}</span>
                          </span>
                        </label>
                      ))}
                      {frameworkPacks.length === 0 && <span className="text-xs text-muted-foreground">No framework rule packs available</span>}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground">MCP scope</p>
                    <div className="flex flex-wrap gap-2">
                      {(["all", "allowlist", "denylist"] as const).map((mode) => (
                        <label key={mode} className="flex items-center gap-1.5 text-sm">
                          <input
                            type="radio"
                            name="edit-mcp-mode"
                            checked={editBundleMcpMode === mode}
                            onChange={() => setEditBundleMcpMode(mode)}
                          />
                          {mode}
                        </label>
                      ))}
                    </div>
                    {editBundleMcpMode !== "all" && (
                      <div className="space-y-2 rounded-md border border-input p-2">
                        {editBundleMcpEntries.map((entry, entryIndex) => {
                          const server = mcpServers.find((s) => s.id === entry.server_id);
                          return (
                            <div key={entryIndex} className="space-y-1 rounded-md border border-border/60 p-2">
                              <div className="flex items-center gap-2">
                                <select
                                  value={entry.server_id}
                                  onChange={(e) => {
                                    const serverId = e.target.value;
                                    const selected = mcpServers.find((s) => s.id === serverId);
                                    setEditBundleMcpEntries((entries) =>
                                      entries.map((en, i) =>
                                        i === entryIndex
                                          ? { server_id: serverId, tool_names: selected ? selected.tool_names : [] }
                                          : en
                                      )
                                    );
                                  }}
                                  className="flex h-8 flex-1 rounded-md border border-input bg-background px-2 text-sm"
                                >
                                  <option value="">Select MCP server</option>
                                  {mcpServers.map((s) => (
                                    <option key={s.id} value={s.id}>{s.name}</option>
                                  ))}
                                </select>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-destructive"
                                  onClick={() => setEditBundleMcpEntries((entries) => entries.filter((_, i) => i !== entryIndex))}
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              </div>
                              {server && server.tool_names.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                  {server.tool_names.map((tool) => (
                                    <label key={tool} className="flex items-center gap-1 text-xs">
                                      <input
                                        type="checkbox"
                                        checked={entry.tool_names.includes(tool)}
                                        onChange={(e) => {
                                          setEditBundleMcpEntries((entries) =>
                                            entries.map((en, i) =>
                                              i === entryIndex
                                                ? {
                                                    ...en,
                                                    tool_names: e.target.checked
                                                      ? [...en.tool_names, tool]
                                                      : en.tool_names.filter((t) => t !== tool),
                                                  }
                                                : en
                                            )
                                          );
                                        }}
                                      />
                                      {tool}
                                    </label>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full text-xs border-dashed"
                          onClick={() => setEditBundleMcpEntries((entries) => [...entries, { server_id: "", tool_names: [] }])}
                        >
                          <Plus className="mr-1 h-3 w-3" /> Add server exception
                        </Button>
                      </div>
                    )}
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <Button variant="outline" onClick={() => setEditingBundleId(null)}>Cancel</Button>
                    <Button
                      onClick={() => updateBundle.mutate()}
                      disabled={updateBundle.isPending || !editBundleName.trim()}
                    >
                      {updateBundle.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Save Changes
                    </Button>
                  </div>
                </div>
              )}

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

              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Framework rule packs</p>
                <div className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-input p-2">
                  {frameworkPacks.map((pack) => (
                    <label key={pack.id} className="flex items-start gap-2 text-sm">
                      <input
                        type="checkbox"
                        className="mt-0.5"
                        checked={newBundleFrameworkPacks.includes(pack.id)}
                        onChange={(e) => {
                          if (e.target.checked) setNewBundleFrameworkPacks((ids) => [...ids, pack.id]);
                          else setNewBundleFrameworkPacks((ids) => ids.filter((id) => id !== pack.id));
                        }}
                      />
                      <span>
                        <span className="font-medium">{pack.name}</span>
                        <span className="ml-1 text-xs text-muted-foreground">v{pack.version} · {pack.rule_count} rules</span>
                        <span className="block text-xs text-muted-foreground">{pack.description}</span>
                      </span>
                    </label>
                  ))}
                  {frameworkPacks.length === 0 && <span className="text-xs text-muted-foreground">No framework rule packs available</span>}
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
      <Card className="overflow-hidden border-border/60 bg-card/50 shadow-sm">
        <CardHeader className="border-b border-border/60 bg-muted/20 pb-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2">
              <CardTitle className="flex items-center gap-2 text-xl">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <KeyRound className="h-5 w-5" />
                </span>
                Client API Keys
              </CardTitle>
              <CardDescription className="max-w-2xl leading-6">
                Create credentials for apps, agents, and browser integrations. Each key inherits a policy bundle and its own limits.
              </CardDescription>
            </div>
            {canEdit && (
              <Button className="gap-2 self-start" onClick={() => setShowCreateKey((value) => !value)}>
                {showCreateKey ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                {showCreateKey ? "Close" : "Create API key"}
              </Button>
            )}
          </div>
          <div className="grid grid-cols-1 gap-3 pt-2 sm:grid-cols-3">
            <div className="rounded-xl border border-border/60 bg-background/70 p-3">
              <div className="flex items-center gap-2 text-xs text-muted-foreground"><Activity className="h-3.5 w-3.5" /> Total keys</div>
              <p className="mt-1 text-2xl font-semibold">{keys.length}</p>
            </div>
            <div className="rounded-xl border border-border/60 bg-background/70 p-3">
              <div className="flex items-center gap-2 text-xs text-muted-foreground"><ShieldCheck className="h-3.5 w-3.5 text-emerald-600" /> Active now</div>
              <p className="mt-1 text-2xl font-semibold">{activeKeyCount}</p>
            </div>
            <div className="rounded-xl border border-border/60 bg-background/70 p-3">
              <div className="flex items-center gap-2 text-xs text-muted-foreground"><Globe2 className="h-3.5 w-3.5 text-sky-600" /> Browser integrations</div>
              <p className="mt-1 text-2xl font-semibold">{browserKeyCount}</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 p-4 md:p-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="relative min-w-0 flex-1 md:max-w-md">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                value={keySearch}
                onChange={(event) => setKeySearch(event.target.value)}
                placeholder="Search keys, bundles, or sources"
                aria-label="Search client API keys"
                className="h-10 w-full rounded-lg border border-input bg-background pl-9 pr-3 text-sm outline-none transition-colors focus:border-primary"
              />
            </div>
            <div className="flex items-center gap-2">
              {(["all", "active", "inactive"] as const).map((filter) => (
                <Button key={filter} variant={keyFilter === filter ? "secondary" : "ghost"} size="sm" onClick={() => setKeyFilter(filter)}>
                  {filter[0].toUpperCase() + filter.slice(1)}
                </Button>
              ))}
            </div>
          </div>

          {showCreateKey && canEdit && (
            <div className="space-y-4 rounded-xl border border-primary/25 bg-primary/[0.03] p-4 md:p-5">
              <div>
                <p className="font-medium">Create a client key</p>
                <p className="mt-1 text-sm text-muted-foreground">Start with a name and policy bundle. Advanced limits and origin controls are below.</p>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <input
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="Name, e.g. support-agent"
                  aria-label="API key name"
                  className="flex h-10 w-full rounded-lg border border-input bg-background px-3 text-sm"
                />
                <select
                  value={newKeyBundleId}
                  onChange={(e) => setNewKeyBundleId(e.target.value)}
                  aria-label="Policy bundle"
                  className="flex h-10 w-full rounded-lg border border-input bg-background px-3 text-sm"
                >
                  <option value="">No bundle (builtin rules only)</option>
                  {bundles.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              </div>
              <details className="rounded-lg border border-border/60 bg-background/60 p-3">
                <summary className="cursor-pointer text-sm font-medium">Advanced key settings</summary>
                <div className="mt-4 space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <select value={newKeyType} onChange={(e) => setNewKeyType(e.target.value as "pysetu" | "mirrored")} className="flex h-10 w-full rounded-lg border border-input bg-background px-3 text-sm">
                      <option value="pysetu">PySetu generated (hg_…)</option>
                      <option value="mirrored">Mirrored provider key</option>
                    </select>
                    <select value={newKeyClientProtocol} onChange={(e) => setNewKeyClientProtocol(e.target.value)} className="flex h-10 w-full rounded-lg border border-input bg-background px-3 text-sm">
                      {CLIENT_PROTOCOL_OPTIONS.map((option) => <option key={option.value || "inherit"} value={option.value}>{option.label}</option>)}
                    </select>
                  </div>
                  {newKeyType === "mirrored" && (
                    <div className="space-y-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-muted-foreground">
                      <p>Register an existing provider key for URL-only migration.</p>
                      <input type="password" value={newMirroredKey} onChange={(e) => setNewMirroredKey(e.target.value)} placeholder="Provider key" className="flex h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" />
                      <label className="flex items-center gap-2"><input type="checkbox" checked={newKeyPassThrough} onChange={(e) => setNewKeyPassThrough(e.target.checked)} /> Forward ingress key upstream</label>
                    </div>
                  )}
                  <ApiKeyLimitsForm limits={newKeyLimits} onChange={(field, value) => setNewKeyLimits((prev) => ({ ...prev, [field]: value }))} disabled={createKey.isPending} />
                  <ApiKeyOriginsForm mode={newKeyOriginsMode} originsText={newKeyOriginsText} onModeChange={setNewKeyOriginsMode} onOriginsTextChange={setNewKeyOriginsText} disabled={createKey.isPending} />
                </div>
              </details>
              <Button
                className="gap-2"
                disabled={!newKeyName.trim() || createKey.isPending || (newKeyType === "mirrored" && newMirroredKey.trim().length < 8)}
                onClick={() => createKey.mutate()}
              >
                {createKey.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                {newKeyType === "mirrored" ? "Register mirrored key" : "Generate key"}
              </Button>
            </div>
          )}

          {filteredKeys.map((key: ApiClientApiKey) => (
            <div key={key.id} className="flex flex-col gap-4 rounded-xl border border-border/60 bg-background/50 p-4 transition-colors hover:border-border md:flex-row md:items-start md:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium">{key.name}</p>
                  <Badge variant={key.is_active ? "success" : "secondary"}>
                    {key.is_active ? "Active" : "Inactive"}
                  </Badge>
                  {key.key_source === "mirrored" && <Badge variant="outline">Mirrored</Badge>}
                  {key.key_source === "mirrored" && key.upstream_pass_through && (
                    <Badge variant="outline" className="border-sky-500/30 text-sky-700 dark:text-sky-300">
                      Pass-through
                    </Badge>
                  )}
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
                <p className="mt-1 text-xs text-muted-foreground">
                  Token saving:{" "}
                  {key.token_saving_enabled == null
                    ? "Inherit tenant default"
                    : key.token_saving_enabled
                      ? key.token_saving_mode || "both"
                      : "Disabled"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Origins:{" "}
                  {originsLabel(
                    originsModeFromKey(key.allowed_api_origins_mode, key.allowed_api_origins),
                    key.allowed_api_origins,
                    tenantOriginCount
                  )}
                </p>
              </div>
              <div className="flex flex-col items-end gap-2">
                {canEdit && (
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={() => revealKey.mutate(key.id)}
                      disabled={
                        !key.revealable || (revealKey.isPending && revealKey.variables === key.id)
                      }
                      title={
                        key.revealable
                          ? "Reveal the full API key"
                          : "This key was created before reveal support and cannot be recovered"
                      }
                    >
                      {revealKey.isPending && revealKey.variables === key.id ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Eye className="h-3 w-3" />
                      )}
                      View key
                    </Button>
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
                    <div className="mt-3">
                      <ApiKeyOriginsForm
                        mode={originsModeFromKey(
                          editingKeyLimits.allowed_api_origins_mode,
                          editingKeyLimits.allowed_api_origins
                        )}
                        originsText={(editingKeyLimits.allowed_api_origins || []).join(", ")}
                        onModeChange={(mode) => {
                          setEditingKeyLimits((prev) => {
                            if (!prev) return null;
                            if (mode === "inherit") return { ...prev, allowed_api_origins: null, allowed_api_origins_mode: "inherit" };
                            if (mode === "allow_all") return { ...prev, allowed_api_origins: [], allowed_api_origins_mode: "allow_all" };
                            return { ...prev, allowed_api_origins_mode: "restrict" };
                          });
                        }}
                        onOriginsTextChange={(text) => {
                          setEditingKeyLimits((prev) =>
                            prev
                              ? {
                                  ...prev,
                                  allowed_api_origins: text
                                    .split(",")
                                    .map((origin) => origin.trim())
                                    .filter(Boolean),
                                  allowed_api_origins_mode: "restrict",
                                }
                              : null
                          );
                        }}
                        disabled={updateKeyLimits.isPending}
                      />
                    </div>
                    {editingKeyLimits.key_source === "mirrored" && (
                      <label className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                        <input
                          type="checkbox"
                          checked={editingKeyLimits.upstream_pass_through}
                          onChange={(e) =>
                            setEditingKeyLimits((prev) =>
                              prev ? { ...prev, upstream_pass_through: e.target.checked } : null
                            )
                          }
                          disabled={updateKeyLimits.isPending}
                        />
                        Forward ingress key to upstream OpenAI-compatible API
                      </label>
                    )}
                    <div className="mt-3 flex justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setEditingKeyLimits(null)}>
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        onClick={() =>
                          updateKeyLimits.mutate({
                            ...editingKeyLimits,
                            allowed_api_origins: originsToPayload(
                              originsModeFromKey(
                                editingKeyLimits.allowed_api_origins_mode,
                                editingKeyLimits.allowed_api_origins
                              ),
                              (editingKeyLimits.allowed_api_origins || []).join(", ")
                            ),
                          })
                        }
                        disabled={updateKeyLimits.isPending}
                      >
                        {updateKeyLimits.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {filteredKeys.length === 0 && (
            <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
              <KeyRound className="mx-auto h-8 w-8 text-muted-foreground/50" />
              <p className="mt-3 font-medium">{keys.length ? "No matching keys" : "No client API keys yet"}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {keys.length ? "Try a different search or filter." : "Create a key to connect an application to the gateway."}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
      )}

      {createdKey && (
        <AppModal
          title="Key created"
          description="Copy this key now — it is shown only once and cannot be recovered later."
          onClose={() => setCreatedKey(null)}
          size="md"
        >
          <div className="space-y-4">
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4">
              <p className="mb-2 text-xs font-medium text-emerald-300">Client API key</p>
              <code className="block break-all rounded bg-black/30 px-2 py-1 font-mono text-xs">
                {createdKey.api_key}
              </code>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                onClick={() => {
                  navigator.clipboard.writeText(createdKey.api_key);
                  setCopiedKey(true);
                  window.setTimeout(() => setCopiedKey(false), 2000);
                }}
              >
                <Copy className="h-3 w-3" />
                {copiedKey ? "Copied!" : "Copy"}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setCreatedKey(null)}>
                Done
              </Button>
            </div>
          </div>
        </AppModal>
      )}

      {revealedKey && (
        <AppModal
          title={revealedKey.name}
          description="Full client API key for this entry. Copy it to your clipboard."
          onClose={() => setRevealedKey(null)}
          size="md"
        >
          <div className="space-y-4">
            <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Client API key</p>
              <code className="block break-all rounded bg-black/30 px-2 py-1 font-mono text-xs">
                {revealedKey.api_key}
              </code>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                onClick={() => {
                  navigator.clipboard.writeText(revealedKey.api_key);
                  setCopiedKey(true);
                  window.setTimeout(() => setCopiedKey(false), 2000);
                }}
              >
                <Copy className="h-3 w-3" />
                {copiedKey ? "Copied!" : "Copy"}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setRevealedKey(null)}>
                Close
              </Button>
            </div>
          </div>
        </AppModal>
      )}
    </div>
  );
}
