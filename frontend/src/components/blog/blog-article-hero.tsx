"use client";

import {
  GatewayHeroGraphic,
  GenaiDlpHeroGraphic,
  McpHeroGraphic,
  RoutingHeroGraphic,
  PolicyHeroGraphic,
  GraphHeroGraphic,
  ComplianceHeroGraphic,
  CompatibilityHeroGraphic,
  ObservabilityHeroGraphic,
  PlatformOpsHeroGraphic,
  IdentityHeroGraphic,
  StudioReportsHeroGraphic,
  McpToolChainsHeroGraphic,
  CopilotHeroGraphic,
  AgenticSecurityHeroGraphic,
} from "@/components/marketing/marketing-feature-graphics";

const FEATURE_GRAPHICS: Record<string, () => React.ReactNode> = {
  "GenAI DLP & Governed RAG": GenaiDlpHeroGraphic,
  "AI Gateway": GatewayHeroGraphic,
  "Universal AI Gateway": CompatibilityHeroGraphic,
  "MCP Governance": McpHeroGraphic,
  "MCP Tool Chains": McpToolChainsHeroGraphic,
  "Microsoft Copilot Governance": CopilotHeroGraphic,
  "Agentic Security": AgenticSecurityHeroGraphic,
  "LLM Router": RoutingHeroGraphic,
  "Policy Studio": PolicyHeroGraphic,
  "Compliance & Audit": ComplianceHeroGraphic,
  "Observability & Monitoring": ObservabilityHeroGraphic,
  "Governance Graph": GraphHeroGraphic,
  "Enterprise Identity & Deployment": IdentityHeroGraphic,
  "Platform Operations": PlatformOpsHeroGraphic,
  "Studio & Reports": StudioReportsHeroGraphic,
  "Financial Services": GenaiDlpHeroGraphic,
  Healthcare: GatewayHeroGraphic,
  "Multi-tenant SaaS": PlatformOpsHeroGraphic,
  "Governance Sandbox": StudioReportsHeroGraphic,
};

export function BlogArticleHero({ feature, image_url }: { feature: string; image_url?: string | null }) {
  if (image_url) {
    return (
      <div className="mt-8 overflow-hidden rounded-2xl border border-border/60 bg-card/40">
        <img src={image_url} alt="Article hero" className="h-64 w-full object-cover md:h-80" />
      </div>
    );
  }
  const Graphic = FEATURE_GRAPHICS[feature] ?? GatewayHeroGraphic;
  return (
    <div className="mt-8 overflow-hidden rounded-2xl border border-border/60 bg-card/40 p-4">
      <Graphic />
    </div>
  );
}
