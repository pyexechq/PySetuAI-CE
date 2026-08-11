import { create } from "zustand";
import {
  DEFAULT_TENANT_FEATURES,
  type TenantFeaturePolicy,
  type TenantFeatures,
  resolveTenantFeatures,
} from "@/lib/tenant-features";

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  displayName?: string;
  logoUrl?: string | null;
  brandTagline?: string;
  qaDashboardEnabled?: boolean;
  features?: TenantFeatures;
  featurePolicy?: TenantFeaturePolicy;
}

interface TenantState {
  currentTenant: Tenant;
  tenants: Tenant[];
  setTenant: (tenant: Tenant) => void;
}

const DEFAULT_TENANT: Tenant = {
  id: "tenant-acme",
  name: "Acme Corporation",
  slug: "acme",
  displayName: "Acme Corporation",
  brandTagline: "Enterprise AI Control Plane",
  qaDashboardEnabled: true,
  features: DEFAULT_TENANT_FEATURES,
};

export const useTenantStore = create<TenantState>((set) => ({
  currentTenant: DEFAULT_TENANT,
  tenants: [DEFAULT_TENANT],
  setTenant: (tenant) =>
    set({
      currentTenant: {
        ...tenant,
        displayName: tenant.displayName ?? tenant.name,
        brandTagline: tenant.brandTagline ?? "Enterprise AI Control Plane",
        features: resolveTenantFeatures(tenant.features, tenant.qaDashboardEnabled),
        qaDashboardEnabled: resolveTenantFeatures(tenant.features, tenant.qaDashboardEnabled).qa_dashboard,
        featurePolicy: tenant.featurePolicy,
      },
    }),
}));

export function tenantBrandName(tenant: Tenant): string {
  return tenant.displayName?.trim() || tenant.name;
}

export function tenantBrandTagline(tenant: Tenant): string {
  return tenant.brandTagline?.trim() || "Enterprise AI Control Plane";
}
