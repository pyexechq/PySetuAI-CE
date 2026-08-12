"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, UserPlus, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function IdentitySettingsPanel() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["identity-settings", token],
    queryFn: () => api.getIdentitySettings(token!),
    enabled: Boolean(token),
  });

  const updateMutation = useMutation({
    mutationFn: (enabled: boolean) =>
      api.updateIdentitySettings(token!, { oidc_jit_provision_enabled: enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["identity-settings"] }),
  });

  const updateDomainsMutation = useMutation({
    mutationFn: (domains: string[] | null) =>
      api.updateIdentitySettings(token!, { allowed_login_domains: domains }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["identity-settings"] }),
  });

  const [domainsText, setDomainsText] = useState("");

  useEffect(() => {
    if (data?.allowed_login_domains) {
      setDomainsText(data.allowed_login_domains.join(", "));
    } else {
      setDomainsText("");
    }
  }, [data]);

  const handleSaveDomains = () => {
    const list = domainsText.split(",").map((d) => d.trim()).filter(Boolean);
    updateDomainsMutation.mutate(list.length > 0 ? list : null);
  };

  const jitEnabled = data?.oidc_jit_provision_enabled ?? false;
  const platformDefault = data?.platform_jit_default ?? false;

  return (
    <>
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <UserPlus className="h-4 w-4" />
          SSO user provisioning
        </CardTitle>
        <CardDescription>
          Control whether unknown SSO users are created automatically on first sign-in (just-in-time
          provisioning).
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading identity settings…
          </p>
        ) : (
          <div className="flex flex-wrap items-start justify-between gap-4 rounded-md border border-border/60 p-4">
            <div className="space-y-2">
              <label className="flex cursor-pointer items-center gap-3">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-input"
                  checked={jitEnabled}
                  disabled={updateMutation.isPending}
                  onChange={(e) => updateMutation.mutate(e.target.checked)}
                />
                <span className="text-sm font-medium">Enable JIT provisioning for this tenant</span>
              </label>
              <p className="text-xs text-muted-foreground">
                When disabled, only users that already exist in PySetu (or linked on first SSO login by
                email) can sign in. When enabled, new IdP users receive a local account on first SSO login.
              </p>
              {platformDefault && (
                <p className="text-xs text-muted-foreground">
                  Platform default for new tenants: {platformDefault ? "JIT on" : "JIT off"} (
                  <code className="rounded bg-muted px-1">OIDC_JIT_PROVISION_DEFAULT</code>).
                </p>
              )}
            </div>
            <Badge variant={jitEnabled ? "default" : "outline"}>
              {jitEnabled ? "JIT enabled" : "JIT disabled"}
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
    
    <Card className="mt-6 border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck className="h-4 w-4" />
          Allowed Login Domains
        </CardTitle>
        <CardDescription>
          Restrict logins and sign-ups to specific email domains. Useful for locking down your tenant to corporate emails.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading settings…
          </p>
        ) : (
          <div className="space-y-4 max-w-md">
            <div>
              <label className="text-sm font-medium">Domain Allowlist (comma separated)</label>
              <textarea
                className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="acme.com, acmecorp.com"
                rows={3}
                value={domainsText}
                onChange={(e) => setDomainsText(e.target.value)}
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Leave empty to allow any email domain.
              </p>
            </div>
            <button
              onClick={handleSaveDomains}
              disabled={updateDomainsMutation.isPending}
              className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              {updateDomainsMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Domains
            </button>
          </div>
        )}
      </CardContent>
    </Card>
    </>
  );
}
