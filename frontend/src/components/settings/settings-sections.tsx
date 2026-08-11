"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import { Building2, Loader2, LogOut, Moon, Save, Sun } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { BrandingLogo } from "@/components/branding/branding-logo";
import { api, type ApiOrganizationSettings } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { tenantBrandName, useTenantStore } from "@/stores/tenant-store";

export function OrganizationSettings() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const { currentTenant } = useTenantStore();
  const canEdit = user?.role === "tenant_admin" || user?.role === "platform_admin";

  const { data, isLoading } = useQuery({
    queryKey: ["organization-settings", token],
    queryFn: () => api.getOrganizationSettings(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  if (isLoading || !data) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading organization settings…
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Organization
          </CardTitle>
          <CardDescription>Tenant profile and your signed-in account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-sm text-muted-foreground">Organization</p>
              <p className="font-medium">{tenantBrandName(currentTenant)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Tenant ID</p>
              <p className="font-mono text-sm">{currentTenant.id}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Signed in as</p>
              <p className="font-medium">{user?.name ?? "—"}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Role</p>
              <Badge variant="secondary">{user?.role?.replace("_", " ") ?? "—"}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <WhiteLabelSettingsForm key={data.id + data.display_name + (data.logo_url ?? "")} settings={data} canEdit={canEdit} />
    </div>
  );
}

function WhiteLabelSettingsForm({
  settings,
  canEdit,
}: {
  settings: ApiOrganizationSettings;
  canEdit: boolean;
}) {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const setTenant = useTenantStore((s) => s.setTenant);

  const [name, setName] = useState(settings.name);
  const [displayName, setDisplayName] = useState(settings.display_name);
  const [tagline, setTagline] = useState(settings.brand_tagline);
  const [logoUrl, setLogoUrl] = useState(settings.logo_url ?? "");

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateOrganizationSettings(token!, {
        name,
        display_name: displayName,
        brand_tagline: tagline,
        logo_url: logoUrl,
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["organization-settings"] });
      setTenant({
        id: updated.id,
        name: updated.name,
        slug: updated.slug,
        displayName: updated.display_name,
        logoUrl: updated.logo_url,
        brandTagline: updated.brand_tagline,
      });
    },
  });

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="text-base">White-label branding</CardTitle>
        <CardDescription>
          Customize the product name, tagline, and logo shown in the sidebar and login page for this tenant.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4 rounded-md border border-border/60 bg-muted/20 p-4">
          <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-lg bg-primary">
            <BrandingLogo logoUrl={logoUrl || null} alt={displayName || name} iconClassName="h-6 w-6 text-primary-foreground" />
          </div>
          <div>
            <p className="font-semibold">{displayName || name}</p>
            <p className="text-sm text-muted-foreground">{tagline || settings.default_tagline}</p>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">Legal organization name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!canEdit}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Display name</label>
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              disabled={!canEdit}
              placeholder={name}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <label className="text-sm font-medium">Tagline</label>
            <input
              value={tagline}
              onChange={(e) => setTagline(e.target.value)}
              disabled={!canEdit}
              placeholder={settings.default_tagline}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <label className="text-sm font-medium">Logo URL</label>
            <input
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
              disabled={!canEdit}
              placeholder="https://…/logo.png"
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none disabled:opacity-50"
            />
            <p className="text-xs text-muted-foreground">HTTPS URL to a square PNG/SVG. Leave empty to use the default shield icon.</p>
          </div>
        </div>

        {canEdit ? (
          <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending || !name.trim()} className="gap-2">
            {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save branding
          </Button>
        ) : (
          <p className="text-xs text-muted-foreground">Tenant Admin role required to edit white-label settings.</p>
        )}
      </CardContent>
    </Card>
  );
}

export function AppearanceSettings() {
  const { theme, setTheme } = useTheme();

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {theme === "dark" ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
          Appearance
        </CardTitle>
        <CardDescription>Theme and display preferences</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            <span className="text-sm">Theme: {theme === "dark" ? "Dark" : "Light"}</span>
          </div>
          <Button variant="outline" size="sm" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            Toggle Theme
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function SettingsSignOut() {
  const { logout } = useAuthStore();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <>
      <Separator />
      <Button variant="destructive" onClick={handleLogout} className="gap-2">
        <LogOut className="h-4 w-4" />
        Sign Out
      </Button>
    </>
  );
}
