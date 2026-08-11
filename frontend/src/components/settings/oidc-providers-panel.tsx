"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { KeyRound, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  formatRoleMappingSummary,
  OidcRoleMappingFields,
  type OidcRoleMapping,
} from "@/components/settings/oidc-role-mapping-fields";
import { ApiError, api, type ApiOidcProvider, type ApiOidcProviderCreateRequest } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const emptyForm: ApiOidcProviderCreateRequest = {
  name: "",
  issuer_url: "",
  client_id: "",
  scopes: "openid profile email",
  role_claim: "groups",
  role_mapping: {},
  enabled: true,
};

function ProviderMappingEditor({
  provider,
  onSaved,
  onCancel,
}: {
  provider: ApiOidcProvider;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const token = useAuthStore((s) => s.token);
  const [roleClaim, setRoleClaim] = useState(provider.role_claim || "groups");
  const [roleMapping, setRoleMapping] = useState<OidcRoleMapping>(provider.role_mapping ?? {});
  const [error, setError] = useState("");

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateOidcProvider(token!, provider.id, {
        role_claim: roleClaim.trim() || "groups",
        role_mapping: roleMapping,
      }),
    onSuccess: () => onSaved(),
    onError: (err) => setError(err instanceof ApiError ? err.message : "Unable to save role mapping."),
  });

  return (
    <div className="mt-3 space-y-3 border-t border-border/60 pt-3">
      <OidcRoleMappingFields
        roleClaim={roleClaim}
        roleMapping={roleMapping}
        onRoleClaimChange={setRoleClaim}
        onRoleMappingChange={setRoleMapping}
        disabled={saveMutation.isPending}
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="flex gap-2">
        <Button size="sm" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
          {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save mapping"}
        </Button>
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

export function OidcProvidersPanel() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ApiOidcProviderCreateRequest>(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [createError, setCreateError] = useState("");
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);

  const { data: providers = [], isLoading } = useQuery({
    queryKey: ["oidc-providers", token],
    queryFn: () => api.listOidcProviders(token!),
    enabled: Boolean(token),
  });

  const createMutation = useMutation({
    mutationFn: () => api.createOidcProvider(token!, form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["oidc-providers"] });
      setForm(emptyForm);
      setShowForm(false);
      setCreateError("");
    },
    onError: (err) =>
      setCreateError(err instanceof ApiError ? err.message : "Unable to create OIDC provider."),
  });

  const deleteMutation = useMutation({
    mutationFn: (providerId: string) => api.deleteOidcProvider(token!, providerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["oidc-providers"] });
      setEditingProviderId(null);
    },
  });

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="h-4 w-4" />
            SSO / OIDC Providers
          </CardTitle>
          <CardDescription>
            Configure IdP metadata and map IdP groups to PySetu roles for SSO sign-in.
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowForm((v) => !v)} className="gap-1">
          <Plus className="h-4 w-4" />
          Add provider
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {showForm && (
          <div className="space-y-3 rounded-md border border-border/60 p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                placeholder="Display name (Okta, Azure AD)"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="flex h-9 rounded-md border border-input bg-background px-3 text-sm"
              />
              <input
                placeholder="Client ID"
                value={form.client_id}
                onChange={(e) => setForm((f) => ({ ...f, client_id: e.target.value }))}
                className="flex h-9 rounded-md border border-input bg-background px-3 text-sm"
              />
              <input
                placeholder="https://your-idp.com/oauth2/default"
                value={form.issuer_url}
                onChange={(e) => setForm((f) => ({ ...f, issuer_url: e.target.value }))}
                className="flex h-9 rounded-md border border-input bg-background px-3 text-sm sm:col-span-2"
              />
              <input
                type="password"
                placeholder="Client secret"
                value={form.client_secret ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, client_secret: e.target.value || undefined }))}
                className="flex h-9 rounded-md border border-input bg-background px-3 text-sm sm:col-span-2"
              />
            </div>

            <OidcRoleMappingFields
              roleClaim={form.role_claim ?? "groups"}
              roleMapping={form.role_mapping ?? {}}
              onRoleClaimChange={(role_claim) => setForm((f) => ({ ...f, role_claim }))}
              onRoleMappingChange={(role_mapping) => setForm((f) => ({ ...f, role_mapping }))}
              disabled={createMutation.isPending}
            />

            {createError && <p className="text-sm text-destructive">{createError}</p>}

            <div className="flex gap-2">
              <Button
                size="sm"
                disabled={!form.name || !form.client_id || !form.issuer_url || createMutation.isPending}
                onClick={() => createMutation.mutate()}
              >
                {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save provider"}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {isLoading ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading providers…
          </p>
        ) : providers.length === 0 ? (
          <p className="text-sm text-muted-foreground">No OIDC providers configured yet.</p>
        ) : (
          <ul className="space-y-2">
            {providers.map((provider) => (
              <li key={provider.id} className="rounded-md border border-border/60 p-3 text-sm">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{provider.name}</span>
                      {!provider.enabled && <Badge variant="warning">Disabled</Badge>}
                      <Badge variant="outline">SSO ready</Badge>
                    </div>
                    <p className="truncate text-xs text-muted-foreground">{provider.issuer_url}</p>
                    <p className="text-xs text-muted-foreground">Client: {provider.client_id}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Claim <code className="rounded bg-muted px-1">{provider.role_claim || "groups"}</code> ·{" "}
                      {formatRoleMappingSummary(provider.role_mapping ?? {})}
                    </p>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setEditingProviderId((current) => (current === provider.id ? null : provider.id))
                      }
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => deleteMutation.mutate(provider.id)}>
                      <Trash2 className="h-4 w-4 text-red-400" />
                    </Button>
                  </div>
                </div>

                {editingProviderId === provider.id && (
                  <ProviderMappingEditor
                    provider={provider}
                    onSaved={() => {
                      queryClient.invalidateQueries({ queryKey: ["oidc-providers"] });
                      setEditingProviderId(null);
                    }}
                    onCancel={() => setEditingProviderId(null)}
                  />
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
