"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useTenantStore } from "@/stores/tenant-store";

export function TenantBrandingSync() {
  const token = useAuthStore((s) => s.token);
  const setTenant = useTenantStore((s) => s.setTenant);

  const { data } = useQuery({
    queryKey: ["organization-settings", token],
    queryFn: () => api.getOrganizationSettings(token!),
    enabled: Boolean(token),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!data) return;
    setTenant({
      id: data.id,
      name: data.name,
      slug: data.slug,
      displayName: data.display_name,
      logoUrl: data.logo_url,
      brandTagline: data.brand_tagline,
    });
  }, [data, setTenant]);

  return null;
}
