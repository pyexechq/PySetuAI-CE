import { create } from "zustand";

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  displayName?: string;
  logoUrl?: string | null;
  brandTagline?: string;
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
      },
    }),
}));

export function tenantBrandName(tenant: Tenant): string {
  return tenant.displayName?.trim() || tenant.name;
}

export function tenantBrandTagline(tenant: Tenant): string {
  return tenant.brandTagline?.trim() || "Enterprise AI Control Plane";
}
