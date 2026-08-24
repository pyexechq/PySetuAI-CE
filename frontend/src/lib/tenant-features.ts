export interface TenantFeatures {
  qa_dashboard: boolean;
  compatibility_center: boolean;
  governance_sandbox: boolean;
  reports: boolean;
  developer_portal: boolean;
}

export interface TenantFeaturePolicyEntry {
  tenant_editable: boolean;
}

export type TenantFeaturePolicy = Record<keyof TenantFeatures, TenantFeaturePolicyEntry>;

export const DEFAULT_TENANT_FEATURES: TenantFeatures = {
  qa_dashboard: true,
  compatibility_center: true,
  governance_sandbox: true,
  reports: true,
  developer_portal: true,
};

export const ROUTE_FEATURE_MAP: Record<string, keyof TenantFeatures> = {
  "/qa-dashboard": "qa_dashboard",
  "/compatibility-center": "compatibility_center",
  "/studio": "governance_sandbox",
  "/reports": "reports",
  "/developer-portal": "developer_portal",
};

export const FEATURE_NAV_LABELS: Record<keyof TenantFeatures, { label: string; description: string }> = {
  qa_dashboard: {
    label: "QA Dashboard",
    description: "Release testing cycles, automated pytest runs, and defect tracking.",
  },
  compatibility_center: {
    label: "Compatibility Center",
    description: "Universal AI Gateway translation stats and compatibility insights.",
  },
  governance_sandbox: {
    label: "Governance Sandbox",
    description: "Prompt lab, policy dry-runs, translation simulator, and MCP testing.",
  },
  reports: {
    label: "Reports",
    description: "Scheduled compliance and governance report exports.",
  },
  developer_portal: {
    label: "Developer Portal",
    description: "Self-service MCP catalogue, API key provisioning, and Agent Playground.",
  },
};

export function resolveTenantFeatures(
  features?: Partial<TenantFeatures> | null,
  legacyQaEnabled?: boolean
): TenantFeatures {
  return {
    ...DEFAULT_TENANT_FEATURES,
    ...features,
    qa_dashboard: legacyQaEnabled ?? features?.qa_dashboard ?? DEFAULT_TENANT_FEATURES.qa_dashboard,
  };
}

export function featureForPath(path: string): keyof TenantFeatures | null {
  if (ROUTE_FEATURE_MAP[path]) return ROUTE_FEATURE_MAP[path];
  for (const [route, feature] of Object.entries(ROUTE_FEATURE_MAP)) {
    if (path.startsWith(`${route}/`)) return feature;
  }
  return null;
}

export function isFeatureEnabled(
  features: TenantFeatures | undefined,
  feature: keyof TenantFeatures
): boolean {
  return (features ?? DEFAULT_TENANT_FEATURES)[feature] !== false;
}

export function isFeatureEditable(
  policy: TenantFeaturePolicy | undefined,
  feature: keyof TenantFeatures
): boolean {
  return policy?.[feature]?.tenant_editable === true;
}
