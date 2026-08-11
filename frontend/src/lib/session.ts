import { clearAuthCookie } from "@/lib/auth-cookie";
import { useAuthStore } from "@/stores/auth-store";

export function isJwtExpired(token: string): boolean {
  try {
    const segment = token.split(".")[1];
    if (!segment) return true;
    const payload = JSON.parse(atob(segment.replace(/-/g, "+").replace(/_/g, "/"))) as { exp?: number };
    if (!payload.exp) return false;
    return Date.now() >= payload.exp * 1000 - 30_000;
  } catch {
    return true;
  }
}

export function handleSessionExpired(): void {
  const { isAuthenticated, logout } = useAuthStore.getState();
  if (!isAuthenticated) return;

  logout();
  clearAuthCookie();

  if (typeof window === "undefined") return;
  if (window.location.pathname.startsWith("/login")) return;

  const url = new URL("/login", window.location.origin);
  url.searchParams.set("expired", "1");
  window.location.assign(url.toString());
}
