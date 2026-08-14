"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Coins, Globe, Loader2, Network, Save } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SectionTabBar } from "@/components/shared/section-chrome";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const TABS = [
  { id: "rates", label: "Rate limits" },
  { id: "saving", label: "Token saving" },
  { id: "tokens", label: "Token budgets" },
  { id: "origins", label: "API origins" },
] as const;

type GatewayTab = (typeof TABS)[number]["id"];

const TAB_IDS = new Set<string>(TABS.map((tab) => tab.id));

export function GatewaySettingsSection() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const canEdit = user?.role === "tenant_admin" || user?.role === "platform_admin";
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const requestedTab = searchParams.get("tab");
  const [tab, setTab] = useState<GatewayTab>(
    requestedTab && TAB_IDS.has(requestedTab) ? (requestedTab as GatewayTab) : "rates"
  );

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
  const [tokenSavingEnabled, setTokenSavingEnabled] = useState(false);
  const [tokenSavingMode, setTokenSavingMode] = useState("both");

  useEffect(() => {
    const next = searchParams.get("tab");
    if (next && TAB_IDS.has(next)) setTab(next as GatewayTab);
  }, [searchParams]);

  useEffect(() => {
    if (data) {
      setRpm(data.ai_rate_limit_rpm ? String(data.ai_rate_limit_rpm) : "");
      setRph(data.ai_rate_limit_rph ? String(data.ai_rate_limit_rph) : "");
      setRpd(data.ai_rate_limit_rpd ? String(data.ai_rate_limit_rpd) : "");
      setTpm(data.ai_token_limit_tpm ? String(data.ai_token_limit_tpm) : "");
      setTph(data.ai_token_limit_tph ? String(data.ai_token_limit_tph) : "");
      setTpd(data.ai_token_limit_tpd ? String(data.ai_token_limit_tpd) : "");
      setOrigins(data.allowed_api_origins ? data.allowed_api_origins.join(", ") : "");
      setTokenSavingEnabled(Boolean(data.token_saving_enabled));
      setTokenSavingMode(data.token_saving_mode || "both");
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
        allowed_api_origins: origins.trim()
          ? origins
              .split(",")
              .map((o) => o.trim())
              .filter(Boolean)
          : null,
        token_saving_enabled: tokenSavingEnabled,
        token_saving_mode: tokenSavingMode,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gateway-settings"] });
    },
  });

  const savingSelectValue = tokenSavingEnabled ? tokenSavingMode || "both" : "off";

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
      <SectionTabBar tabs={TABS} active={tab} onChange={setTab} />

      <Card className="border-border/60 bg-card/50">
        {tab === "rates" && (
          <>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-5 w-5" />
                Request rate limits
              </CardTitle>
              <CardDescription>
                Tenant-wide AI request caps. Leave blank for no limit. Token saving default is on the Token saving tab.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Requests per minute</label>
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
                  <label className="text-sm font-medium">Requests per hour</label>
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
                  <label className="text-sm font-medium">Requests per day</label>
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
            </CardContent>
          </>
        )}

        {tab === "saving" && (
          <>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Coins className="h-5 w-5" />
                Token saving default
              </CardTitle>
              <CardDescription>
                Tenant default for ingress compression (JSON→TOON and markdown stripping). Client API keys can inherit
                this or override it.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="max-w-md space-y-2">
                <label className="text-sm font-medium" htmlFor="token-saving-default">
                  Default for keys that inherit
                </label>
                <select
                  id="token-saving-default"
                  value={savingSelectValue}
                  disabled={!canEdit}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (value === "off") {
                      setTokenSavingEnabled(false);
                      return;
                    }
                    setTokenSavingEnabled(true);
                    setTokenSavingMode(value);
                  }}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
                >
                  <option value="off">Disabled</option>
                  <option value="both">Enabled — JSON→TOON + strip markdown</option>
                  <option value="json_to_toon">Enabled — JSON→TOON only</option>
                  <option value="strip_markdown">Enabled — strip markdown only</option>
                </select>
                <p className="text-xs text-muted-foreground">
                  Applies when a key is set to Inherit tenant default. Override a key under{" "}
                  <Link href="/settings/api-keys" className="underline underline-offset-2">
                    Client API keys
                  </Link>
                  .
                </p>
              </div>
            </CardContent>
          </>
        )}

        {tab === "tokens" && (
          <>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-5 w-5" />
                Token budgets
              </CardTitle>
              <CardDescription>
                Tenant-wide AI token caps across all gateway traffic. Leave blank for no limit.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Tokens per minute</label>
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
                  <label className="text-sm font-medium">Tokens per hour</label>
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
                  <label className="text-sm font-medium">Tokens per day</label>
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
            </CardContent>
          </>
        )}

        {tab === "origins" && (
          <>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Allowed API origins
              </CardTitle>
              <CardDescription>
                Restrict gateway requests that use client API keys to specific HTTP origins (CORS allowlist).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="max-w-md space-y-2">
                <label className="text-sm font-medium">Origin allowlist (comma separated)</label>
                <textarea
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="https://acme.com, https://app.acme.com"
                  rows={3}
                  value={origins}
                  disabled={!canEdit}
                  onChange={(e) => setOrigins(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Leave empty to allow any origin. Server-to-server calls typically do not send an Origin header.
                </p>
              </div>
            </CardContent>
          </>
        )}

        <CardContent className="border-t border-border/60 pt-4">
          {canEdit ? (
            <Button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              className="gap-2"
            >
              {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save gateway settings
            </Button>
          ) : (
            <p className="text-xs text-muted-foreground">Tenant Admin role required to edit gateway limits.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
