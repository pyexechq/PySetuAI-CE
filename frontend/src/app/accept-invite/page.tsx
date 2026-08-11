"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api } from "@/lib/api";
import { useAuthStore, type UserRole } from "@/stores/auth-store";
import { useTenantStore } from "@/stores/tenant-store";

function AcceptInviteContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setSession = useAuthStore((s) => s.login);
  const setTenant = useTenantStore((s) => s.setTenant);
  const tokenParam = searchParams.get("token") ?? "";

  const [previewLoading, setPreviewLoading] = useState(true);
  const [previewError, setPreviewError] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    if (!tokenParam) {
      setPreviewError("Missing invite token.");
      setPreviewLoading(false);
      return;
    }

    void api
      .previewInvite(tokenParam)
      .then((preview) => {
        setTenantName(preview.tenant_name);
        setEmail(preview.email);
      })
      .catch((err) => {
        setPreviewError(err instanceof ApiError ? err.message : "Invalid or expired invite.");
      })
      .finally(() => setPreviewLoading(false));
  }, [tokenParam]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirmPassword) {
      setSubmitError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    setSubmitError("");
    try {
      const result = await api.acceptInvite({
        token: tokenParam,
        password,
        name: name || undefined,
      });
      const user = await api.getCurrentUser(result.access_token);
      const org = await api.getOrganizationSettings(result.access_token);
      setSession(
        {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role as UserRole,
          tenantId: user.tenant_id,
        },
        result.access_token
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
      setSubmitError(err instanceof ApiError ? err.message : "Unable to accept invite.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Accept your invite</CardTitle>
          <CardDescription>
            {previewLoading
              ? "Validating invite…"
              : previewError
                ? previewError
                : `Join ${tenantName} as ${email}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {previewLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading invite…
            </div>
          ) : previewError ? null : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="name" className="text-sm font-medium">
                  Your name
                </label>
                <input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                  placeholder="Alex Admin"
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
                  minLength={8}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="confirmPassword" className="text-sm font-medium">
                  Confirm password
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
                />
              </div>
              {submitError && <p className="text-sm text-destructive">{submitError}</p>}
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Setting up account…
                  </>
                ) : (
                  "Activate account"
                )}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <AcceptInviteContent />
    </Suspense>
  );
}
