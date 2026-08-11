"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore, canAccessRoute } from "@/stores/auth-store";

const PUBLIC_ROUTES = ["/login", "/platform/login", "/terms", "/privacy", "/cookies", "/legal/security"];

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user } = useAuthStore();

  useEffect(() => {
    if (pathname.startsWith("/platform")) return;
    if (pathname === "/" && !isAuthenticated) return;
    if (PUBLIC_ROUTES.includes(pathname)) return;

    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }

    if (user?.role === "platform_admin") {
      router.replace("/platform");
      return;
    }

    if (user && !canAccessRoute(user.role, pathname)) {
      router.replace("/");
    }
  }, [isAuthenticated, user, pathname, router]);

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

  return <>{children}</>;
}
