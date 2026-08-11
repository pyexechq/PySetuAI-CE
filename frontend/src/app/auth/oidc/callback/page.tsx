"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api } from "@/lib/api";
import { useAuthStore, type UserRole } from "@/stores/auth-store";
import { useTenantStore } from "@/stores/tenant-store";

export default function OidcCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuthStore((s) => s.login);
  const setTenant = useTenantStore((s) => s.setTenant);
  const [error, setError] = useState("");

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const providerError = searchParams.get("error_description") || searchParams.get("error");

    if (providerError) {
      setError(providerError);
      return;
    }
    if (!code || !state) {
      setError("Missing OIDC authorization code or state.");
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        const tokenResponse = await api.completeOidcLogin({ code, state });
        const user = await api.getCurrentUser(tokenResponse.access_token);
        const org = await api.getOrganizationSettings(tokenResponse.access_token);

        if (cancelled) return;

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
        router.replace("/");
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? err.message || "SSO sign-in failed."
            : "SSO sign-in failed. Check that the API and Redis are running."
        );
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [login, router, searchParams, setTenant]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md border-border/60">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Completing SSO sign-in</CardTitle>
          <CardDescription>Exchanging authorization code for your HelixGuard session…</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-3 text-sm">
          {!error ? (
            <>
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <p className="text-muted-foreground">Please wait…</p>
            </>
          ) : (
            <p className="text-center text-destructive">{error}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
