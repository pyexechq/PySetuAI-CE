"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BrandingLogo } from "@/components/branding/branding-logo";
import { TenantLoginPanel } from "@/components/auth/tenant-login-panel";
import { api } from "@/lib/api";

const DEFAULT_TAGLINE = "Governance, Gateway, and Guardrails across the Agentic Frontier";

function LoginFormInner() {
  const searchParams = useSearchParams();
  const initialTenant = searchParams.get("tenant") ?? searchParams.get("tenant_slug") ?? "acme";
  const [brandName, setBrandName] = useState("PySetu AI");
  const [brandTagline, setBrandTagline] = useState(DEFAULT_TAGLINE);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);

  useEffect(() => {
    const slug = initialTenant.trim().toLowerCase();
    if (!slug) return;

    api
      .getPublicTenantBranding(slug)
      .then((branding) => {
        setBrandName(branding.display_name || branding.name);
        setBrandTagline(branding.brand_tagline || DEFAULT_TAGLINE);
        setLogoUrl(branding.logo_url);
      })
      .catch(() => {
        setBrandName("PySetu AI");
        setBrandTagline(DEFAULT_TAGLINE);
        setLogoUrl(null);
      });
  }, [initialTenant]);

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
          <TenantLoginPanel initialTenantSlug={initialTenant} />
        </CardContent>
      </Card>
    </div>
  );
}

export function LoginForm() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <LoginFormInner />
    </Suspense>
  );
}
