import { create } from "zustand";
import { persist } from "zustand/middleware";
import { clearAuthCookie, setAuthCookie } from "@/lib/auth-cookie";
import { isJwtExpired } from "@/lib/session";
import {
  featureForPath,
  isFeatureEnabled,
  resolveTenantFeatures,
  type TenantFeatures,
} from "@/lib/tenant-features";

export type UserRole =
  | "platform_admin"
  | "tenant_admin"
  | "security_admin"
  | "compliance_officer"
  | "auditor"
  | "developer";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  tenantId: string;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (user: AuthUser, token: string) => void;
  logout: () => void;
  updateUser: (updates: Partial<AuthUser>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (user, token) => {
        setAuthCookie(token);
        set({ user, token, isAuthenticated: true });
      },
      logout: () => {
        clearAuthCookie();
        set({ user: null, token: null, isAuthenticated: false });
      },
      updateUser: (updates) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        }));
      },
    }),
    {
      name: "pysetu-auth",
      onRehydrateStorage: () => (state) => {
        if (!state?.token) return;
        if (isJwtExpired(state.token)) {
          useAuthStore.getState().logout();
          return;
        }
        setAuthCookie(state.token);
      },
    }
  )
);

export const roleRouteAccess: Record<UserRole, string[]> = {
  platform_admin: ["*"],
  tenant_admin: ["*"],
  security_admin: ["/", "/ai-gateway", "/compatibility-center", "/mcp-governance", "/llm-router", "/policy-studio", "/governance-graph", "/data-protection", "/monitoring", "/audit-explorer", "/qa-dashboard", "/settings"],
  compliance_officer: ["/", "/compliance", "/audit-explorer", "/data-protection", "/reports", "/qa-dashboard", "/settings"],
  auditor: ["/", "/audit-explorer", "/compliance", "/reports", "/monitoring", "/qa-dashboard"],
  developer: ["/", "/studio", "/mcp-governance", "/mcp-portal", "/llm-router", "/policy-studio", "/governance-graph", "/monitoring", "/qa-dashboard", "/settings"],
};

export function canAccessRoute(role: UserRole, path: string): boolean {
  const allowed = roleRouteAccess[role] || [];
  if (allowed.includes("*")) return true;
  return allowed.some((route) => path === route || path.startsWith(`${route}/`));
}

export function isQaDashboardEnabled(tenant: { features?: TenantFeatures; qaDashboardEnabled?: boolean } | null | undefined): boolean {
  return resolveTenantFeatures(tenant?.features, tenant?.qaDashboardEnabled).qa_dashboard;
}

export function canAccessTenantModule(
  tenant: { features?: TenantFeatures; qaDashboardEnabled?: boolean } | null | undefined,
  path: string
): boolean {
  const feature = featureForPath(path);
  if (!feature) return true;
  const features = resolveTenantFeatures(tenant?.features, tenant?.qaDashboardEnabled);
  return isFeatureEnabled(features, feature);
}
