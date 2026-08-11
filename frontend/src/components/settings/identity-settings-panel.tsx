"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, UserPlus } from "lucide-react";
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

  const jitEnabled = data?.oidc_jit_provision_enabled ?? false;
  const platformDefault = data?.platform_jit_default ?? false;

  return (
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
                When disabled, only users that already exist in HelixGuard (or linked on first SSO login by
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
  );
}
