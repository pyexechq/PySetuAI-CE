"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore, canAccessRoute, canAccessTenantModule } from "@/stores/auth-store";
import { useTenantStore } from "@/stores/tenant-store";

const PUBLIC_ROUTES = ["/login", "/accept-invite", "/auth/oidc/callback", "/platform/login", "/terms", "/privacy", "/cookies", "/legal/security"];

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user } = useAuthStore();
  const currentTenant = useTenantStore((s) => s.currentTenant);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (pathname.startsWith("/platform")) return;
    if (pathname === "/" && !isAuthenticated) return;
    if (PUBLIC_ROUTES.includes(pathname)) return;

    if (!isAuthenticated) {
      const next = pathname === "/login" ? "" : `?next=${encodeURIComponent(pathname)}`;
      router.replace(`/login${next}`);
      return;
    }

    if (user?.role === "platform_admin") {
      router.replace("/platform");
      return;
    }

    if (user && !canAccessRoute(user.role, pathname)) {
      router.replace("/");
      return;
    }

    if (user && !canAccessTenantModule(currentTenant, pathname)) {
      router.replace("/");
    }
  }, [hydrated, isAuthenticated, user, pathname, router, currentTenant]);

  if (!hydrated) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (pathname.startsWith("/platform")) {
    return <>{children}</>;
  }

  if (pathname === "/" && !isAuthenticated) {
    return <>{children}</>;
  }

  if (PUBLIC_ROUTES.includes(pathname)) {
    return <>{children}</>;
  }

  if (!isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (user?.role === "platform_admin") {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (user && !canAccessRoute(user.role, pathname)) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 bg-background p-6 text-center">
        <p className="text-lg font-semibold">Access denied</p>
        <p className="max-w-md text-sm text-muted-foreground">
          Your role ({user.role?.replace("_", " ") || "unknown"}) does not have access to this page.
        </p>
        <button
          type="button"
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground"
          onClick={() => router.replace("/")}
        >
          Go to Dashboard
        </button>
      </div>
    );
  }

  if (user && !canAccessTenantModule(currentTenant, pathname)) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 bg-background p-6 text-center">
        <p className="text-lg font-semibold">Module unavailable</p>
        <p className="max-w-md text-sm text-muted-foreground">
          This module is disabled for your tenant. Contact your tenant administrator or SaaS operator to enable it.
        </p>
        <button
          type="button"
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground"
          onClick={() => router.replace("/")}
        >
          Go to Dashboard
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
