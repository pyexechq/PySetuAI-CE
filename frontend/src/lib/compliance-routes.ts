export const COMPLIANCE_MODULE_ROUTES: Record<string, string> = {
  "Policy Studio": "/policy-studio",
  "Audit Explorer": "/audit-explorer",
  "Security Center": "/monitoring?tab=security",
  Observability: "/monitoring?tab=traces",
  Monitoring: "/monitoring",
  "LLM Router": "/llm-router",
  "MCP Governance": "/mcp-governance",
  "Governance Sandbox": "/studio",
  "Compatibility Center": "/compatibility-center",
  Reports: "/reports",
  "Data Protection": "/data-protection",
  Settings: "/settings/organization",
  "Compliance Center": "/compliance",
};

export function complianceFrameworkSlug(name: string): string {
  const map: Record<string, string> = {
    GDPR: "gdpr",
    HIPAA: "hipaa",
    "SOC 2 Type II": "soc2",
    "ISO 27001": "iso27001",
    "NIST AI RMF": "nist-ai-rmf",
  };
  return map[name] ?? name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}
