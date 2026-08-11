"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { KeyRound, Loader2, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type ApiOidcProvider, type ApiOidcProviderCreateRequest } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const emptyForm: ApiOidcProviderCreateRequest = {
  name: "",
  issuer_url: "",
  client_id: "",
  scopes: "openid profile email",
  enabled: true,
};

export function OidcProvidersPanel() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ApiOidcProviderCreateRequest>(emptyForm);
  const [showForm, setShowForm] = useState(false);

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
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (providerId: string) => api.deleteOidcProvider(token!, providerId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["oidc-providers"] }),
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
            Configure IdP metadata. Users must already exist locally unless JIT provisioning is enabled.
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowForm((v) => !v)} className="gap-1">
          <Plus className="h-4 w-4" />
          Add provider
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {showForm && (
          <div className="grid gap-3 rounded-md border border-border/60 p-4 sm:grid-cols-2">
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
            <div className="flex gap-2 sm:col-span-2">
              <Button
                size="sm"
                disabled={!form.name || !form.client_id || !form.issuer_url || createMutation.isPending}
                onClick={() => createMutation.mutate()}
              >
                {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
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
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{provider.name}</span>
                      {!provider.enabled && <Badge variant="warning">Disabled</Badge>}
                      <Badge variant="outline">SSO ready</Badge>
                    </div>
                    <p className="truncate text-xs text-muted-foreground">{provider.issuer_url}</p>
                    <p className="text-xs text-muted-foreground">Client: {provider.client_id}</p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => deleteMutation.mutate(provider.id)}>
                    <Trash2 className="h-4 w-4 text-red-400" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
