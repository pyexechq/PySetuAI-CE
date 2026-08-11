"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BrandingLogo } from "@/components/branding/branding-logo";
import { ApiError, api, type ApiPublicOidcProvider } from "@/lib/api";
import { useAuthStore, type UserRole } from "@/stores/auth-store";
import { useTenantStore } from "@/stores/tenant-store";

const DEFAULT_TAGLINE = "Enterprise AI Control Plane";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuthStore((s) => s.login);
  const setTenant = useTenantStore((s) => s.setTenant);
  const [email, setEmail] = useState("admin@acme.com");
  const [password, setPassword] = useState("demo1234");
  const [tenantSlug, setTenantSlug] = useState("acme");
  const [brandName, setBrandName] = useState("HelixGuard AI");
  const [brandTagline, setBrandTagline] = useState(DEFAULT_TAGLINE);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [oidcProviders, setOidcProviders] = useState<ApiPublicOidcProvider[]>([]);
  const [ssoLoading, setSsoLoading] = useState<string | null>(null);
  const [error, setError] = useState(
    searchParams.get("expired") === "1" ? "Your session expired. Please sign in again." : ""
  );
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const slug = tenantSlug.trim().toLowerCase();
    if (!slug) return;

    const timer = setTimeout(() => {
      api
        .getPublicTenantBranding(slug)
        .then((branding) => {
          setBrandName(branding.display_name || branding.name);
          setBrandTagline(branding.brand_tagline || DEFAULT_TAGLINE);
          setLogoUrl(branding.logo_url);
        })
        .catch(() => {
          setBrandName("HelixGuard AI");
          setBrandTagline(DEFAULT_TAGLINE);
          setLogoUrl(null);
        });

      api
        .listPublicOidcProviders(slug)
        .then((providers) => setOidcProviders(providers.filter((p) => p.login_available)))
        .catch(() => setOidcProviders([]));
    }, 300);

    return () => clearTimeout(timer);
  }, [tenantSlug]);

  async function handleSsoLogin(providerId: string) {
    setError("");
    setSsoLoading(providerId);
    try {
      const slug = tenantSlug.trim().toLowerCase();
      const result = await api.startOidcLogin(slug, providerId);
      window.location.href = result.authorization_url;
    } catch (err) {
      setSsoLoading(null);
      setError(err instanceof ApiError ? err.message : "Unable to start SSO sign-in.");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const tokenResponse = await api.login({ email, password, tenant_slug: tenantSlug });
      const user = await api.getCurrentUser(tokenResponse.access_token);
      const org = await api.getOrganizationSettings(tokenResponse.access_token);

      login(
        {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role as UserRole,
          tenantId: user.tenant_id,
        },
        tokenResponse.access_token
      );
      setTenant({
        id: org.id,
        name: org.name,
        slug: org.slug,
        displayName: org.display_name,
        logoUrl: org.logo_url,
        brandTagline: org.brand_tagline,
      });
      router.replace(user.role === "platform_admin" ? "/platform" : "/");
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.status === 401
            ? "Invalid email, password, or tenant."
            : "Unable to sign in. Check that the API server is running."
          : "Unable to sign in. Check that the API server is running.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md border-border/60">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center overflow-hidden rounded-xl bg-primary/10">
            <BrandingLogo logoUrl={logoUrl} alt={brandName} iconClassName="h-6 w-6 text-primary" className="p-1" />
          </div>
          <CardTitle className="text-xl">{brandName}</CardTitle>
          <CardDescription>{brandTagline} — Sign in to continue</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="tenant" className="text-sm font-medium">
                Tenant
              </label>
              <input
                id="tenant"
                type="text"
                value={tenantSlug}
                onChange={(e) => setTenantSlug(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                placeholder="acme"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                placeholder="admin@acme.com"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                placeholder="••••••••"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            {oidcProviders.length > 0 && (
              <div className="space-y-2 rounded-md border border-border/60 bg-muted/20 p-3">
                <p className="text-xs font-medium text-muted-foreground">Or continue with SSO</p>
                <div className="flex flex-wrap gap-2">
                  {oidcProviders.map((provider) => (
                    <Button
                      key={provider.id}
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={Boolean(ssoLoading)}
                      onClick={() => handleSsoLogin(provider.id)}
                    >
                      {ssoLoading === provider.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        `Sign in with ${provider.name}`
                      )}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign In"
              )}
            </Button>
            <div className="space-y-1 text-center text-xs text-muted-foreground">
              <p>Demo: admin@acme.com / demo1234 (tenant: acme)</p>
              <p>Also: security@acme.com, auditor@acme.com, compliance@acme.com, developer@acme.com</p>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
