"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Network, Save, Loader2, Globe } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function GatewaySettingsSection() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const canEdit = user?.role === "tenant_admin" || user?.role === "platform_admin";
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["gateway-settings", token],
    queryFn: () => api.getGatewaySettings(token!),
    enabled: Boolean(token),
  });

  const [rpm, setRpm] = useState<string>("");
  const [rph, setRph] = useState<string>("");
  const [rpd, setRpd] = useState<string>("");
  const [tpm, setTpm] = useState<string>("");
  const [tph, setTph] = useState<string>("");
  const [tpd, setTpd] = useState<string>("");
  const [origins, setOrigins] = useState<string>("");

  useEffect(() => {
    if (data) {
      setRpm(data.ai_rate_limit_rpm ? String(data.ai_rate_limit_rpm) : "");
      setRph(data.ai_rate_limit_rph ? String(data.ai_rate_limit_rph) : "");
      setRpd(data.ai_rate_limit_rpd ? String(data.ai_rate_limit_rpd) : "");
      setTpm(data.ai_token_limit_tpm ? String(data.ai_token_limit_tpm) : "");
      setTph(data.ai_token_limit_tph ? String(data.ai_token_limit_tph) : "");
      setTpd(data.ai_token_limit_tpd ? String(data.ai_token_limit_tpd) : "");
      setOrigins(data.allowed_api_origins ? data.allowed_api_origins.join(", ") : "");
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateGatewaySettings(token!, {
        ai_rate_limit_rpm: rpm ? parseInt(rpm, 10) : null,
        ai_rate_limit_rph: rph ? parseInt(rph, 10) : null,
        ai_rate_limit_rpd: rpd ? parseInt(rpd, 10) : null,
        ai_token_limit_tpm: tpm ? parseInt(tpm, 10) : null,
        ai_token_limit_tph: tph ? parseInt(tph, 10) : null,
        ai_token_limit_tpd: tpd ? parseInt(tpd, 10) : null,
        allowed_api_origins: origins.trim() ? origins.split(",").map(o => o.trim()).filter(Boolean) : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gateway-settings"] });
    },
  });

  if (isLoading || !data) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading gateway settings…
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-5 w-5" />
            Gateway AI Rate Limits
          </CardTitle>
          <CardDescription>
            Configure global AI rate limits and budgets for your tenant. Leave blank for no limit.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Requests Per Minute (RPM)</label>
              <input
                type="number"
                min="0"
                value={rpm}
                onChange={(e) => setRpm(e.target.value)}
                disabled={!canEdit}
                placeholder="No limit"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Requests Per Hour (RPH)</label>
              <input
                type="number"
                min="0"
                value={rph}
                onChange={(e) => setRph(e.target.value)}
                disabled={!canEdit}
                placeholder="No limit"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Requests Per Day (RPD)</label>
              <input
                type="number"
                min="0"
                value={rpd}
                onChange={(e) => setRpd(e.target.value)}
                disabled={!canEdit}
                placeholder="No limit"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
              />
            </div>
          </div>

          {canEdit ? (
            <Button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              className="mt-4 gap-2"
            >
              {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save Limits
            </Button>
          ) : (
            <p className="mt-4 text-xs text-muted-foreground">
              Tenant Admin role required to edit gateway limits.
            </p>
          )}
        </CardContent>
      </Card>
      
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-5 w-5" />
            Gateway AI Token Budgets
          </CardTitle>
          <CardDescription>
            Configure global AI token budgets for your tenant. Leave blank for no limit.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Tokens Per Minute (TPM)</label>
              <input
                type="number"
                min="0"
                value={tpm}
                onChange={(e) => setTpm(e.target.value)}
                disabled={!canEdit}
                placeholder="No limit"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Tokens Per Hour (TPH)</label>
              <input
                type="number"
                min="0"
                value={tph}
                onChange={(e) => setTph(e.target.value)}
                disabled={!canEdit}
                placeholder="No limit"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Tokens Per Day (TPD)</label>
              <input
                type="number"
                min="0"
                value={tpd}
                onChange={(e) => setTpd(e.target.value)}
                disabled={!canEdit}
                placeholder="No limit"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
              />
            </div>
          </div>

          {canEdit ? (
            <Button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              className="mt-4 gap-2"
            >
              {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save Limits
            </Button>
          ) : (
            <p className="mt-4 text-xs text-muted-foreground">
              Tenant Admin role required to edit gateway limits.
            </p>
          )}
        </CardContent>
      </Card>
      
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Allowed API Origins
          </CardTitle>
          <CardDescription>
            Restrict Gateway API requests using Client Keys to specific HTTP origins (CORS allowlist).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 max-w-md">
            <div>
              <label className="text-sm font-medium">API Origin Allowlist (comma separated)</label>
              <textarea
                className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="https://acme.com, https://app.acme.com"
                rows={3}
                value={origins}
                disabled={!canEdit}
                onChange={(e) => setOrigins(e.target.value)}
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Leave empty to allow requests from any origin. Note: Server-to-server calls don't send Origins.
              </p>
            </div>
            {canEdit ? (
              <Button
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
                className="gap-2"
              >
                {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save Origins
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground">
                Tenant Admin role required to edit allowed origins.
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
