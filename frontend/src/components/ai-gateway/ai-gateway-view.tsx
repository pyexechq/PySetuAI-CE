"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRightLeft,
  CheckCircle2,
  Cloud,
  Copy,
  Check,
  Route,
  Radar,
  Settings2,
  Shield,
  Globe,
  Zap,
  Server,
} from "lucide-react";
import { GatewayTester } from "@/components/ai-gateway/gateway-tester";
import { RagGatewayTester } from "@/components/ai-gateway/rag-gateway-tester";
import { CompatibilityCenterView } from "@/components/compatibility-center/compatibility-center-view";
import { TenantEdgeMeshPanel } from "@/components/settings/tenant-edge-mesh-panel";
import { MetricCard } from "@/components/dashboard/metric-card";
import { QuickLinkPills, SectionTabBar } from "@/components/shared/section-chrome";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { API_BASE, api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const QUICK_LINKS = [
  { href: "/monitoring", label: "Monitoring", icon: Radar },
  { href: "/llm-router?tab=gateway", label: "Gateway & aliases", icon: ArrowRightLeft },
  { href: "/llm-router", label: "LLM Router", icon: Route },
] as const;

const TABS = [
  { id: "connect", label: "Connect & Endpoints" },
  { id: "edge-mesh", label: "Edge Mesh Nodes" },
  { id: "test", label: "Test console" },
  { id: "rag", label: "Governed RAG" },
  { id: "compatibility", label: "Compatibility" },
] as const;

type GatewayTab = (typeof TABS)[number]["id"];
const TAB_IDS = new Set<string>(TABS.map((t) => t.id));

function gatewayHttpMethod(endpoint: string): "GET" | "POST" {
  return endpoint === "/v1/models" || endpoint === "/models" ? "GET" : "POST";
}

function buildSampleCurl(endpoint: string, origin: string = "https://pysetu.io"): string {
  const cleanEndpoint = endpoint.startsWith("/api/v1") ? endpoint.replace("/api/v1", "/v1") : endpoint;
  const url = `${origin}${cleanEndpoint}`;
  const authHeader = "--header 'Authorization: Bearer YOUR_TOKEN_HERE'";
  const methodFlag = gatewayHttpMethod(cleanEndpoint) === "POST" ? "--request POST \\\n" : "";

  if (cleanEndpoint.includes(":generateContent") || cleanEndpoint.startsWith("/v1beta")) {
    return `curl --location '${origin}/v1beta/models/gemini-1.5-pro:generateContent' \\
--request POST \\
${authHeader} \\
--header 'Content-Type: application/json' \\
--data '{
  "contents": [
    {
      "parts": [
        {
          "text": "Hello from PySetu Gemini Gateway"
        }
      ]
    }
  ]
}'`;
  }

  if (cleanEndpoint === "/v1/chat/completions") {
    return `curl --location '${origin}/v1/chat/completions' \\
${methodFlag}${authHeader} \\
--header 'Content-Type: application/json' \\
--data '{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": "Hello from PySetu"
    }
  ]
}'`;
  }

  return `curl --location '${url}' \\
${authHeader}`;
}

const EMPTY_GATEWAY_STATUS = {
  status: "unknown",
  openai_compatible: false,
  gemini_compatible: false,
  requests_today: 0,
  blocked_today: 0,
  endpoints: [
    "/v1/chat/completions",
    "/v1/models",
    "/v1/mcp",
    "/v1beta/models/{model}:generateContent",
  ],
  proxy_mode: "none",
  opa_available: false,
};

const PIPELINE_STEPS = [
  "PII & secret detection on ingress",
  "Policy engine evaluation",
  "LLM router selection",
  "Output leakage scan on egress",
  "Full audit trace logging",
];

function upstreamLabel(status: {
  openai_compatible: boolean;
  gemini_compatible: boolean;
  proxy_mode?: string;
}): string {
  const parts: string[] = [];
  if (status.openai_compatible) parts.push("OpenAI");
  if (status.gemini_compatible) parts.push("Gemini");
  if (status.proxy_mode === "ollama") parts.push("Ollama");
  else if (status.proxy_mode && status.proxy_mode !== "none") parts.push(status.proxy_mode);
  return parts.length > 0 ? parts.join(" · ") : "Not configured";
}

type BadgeVariant = "default" | "secondary" | "destructive" | "success" | "warning" | "outline";
interface StatusMeta {
  text: string;
  variant: BadgeVariant;
}

function gatewayStatusGradient(status: string, opaAvailable: boolean): string {
  const normalized = (status || "unknown").toLowerCase();
  if (normalized === "operational" || normalized === "healthy") {
    return opaAvailable
      ? "bg-gradient-to-r from-emerald-500 to-emerald-700"
      : "bg-gradient-to-r from-amber-500 to-amber-700";
  }
  if (normalized === "degraded" || normalized === "warning") {
    return "bg-gradient-to-r from-amber-500 to-amber-700";
  }
  if (normalized === "offline" || normalized === "error" || normalized === "unavailable") {
    return "bg-gradient-to-r from-rose-500 to-rose-700";
  }
  return "bg-gradient-to-r from-slate-500 to-slate-700";
}

function gatewayStatusMeta(status: string, opaAvailable: boolean): StatusMeta {
  const normalized = (status || "unknown").toLowerCase();
  if (normalized === "operational" || normalized === "healthy") {
    return { text: opaAvailable ? "Online" : "No policy engine", variant: opaAvailable ? "success" : "warning" };
  }
  if (normalized === "degraded" || normalized === "warning") {
    return { text: "Degraded", variant: "warning" };
  }
  if (normalized === "offline" || normalized === "error" || normalized === "unavailable") {
    return { text: "Offline", variant: "destructive" };
  }
  return { text: "Unknown", variant: "secondary" };
}

function upstreamStatusMeta(status: {
  openai_compatible: boolean;
  gemini_compatible: boolean;
  proxy_mode?: string;
}): StatusMeta {
  const hasAny = status.openai_compatible || status.gemini_compatible || status.proxy_mode === "ollama";
  if (!hasAny) return { text: "Not configured", variant: "secondary" };
  if (status.proxy_mode === "ollama") return { text: "Ollama proxy", variant: "warning" };
  return { text: "Connected", variant: "success" };
}

function upstreamGradient(status: {
  openai_compatible: boolean;
  gemini_compatible: boolean;
  proxy_mode?: string;
}): string {
  const hasAny = status.openai_compatible || status.gemini_compatible || status.proxy_mode === "ollama";
  if (!hasAny) return "bg-gradient-to-r from-slate-500 to-slate-700";
  if (status.proxy_mode === "ollama") return "bg-gradient-to-r from-amber-500 to-amber-700";
  return "bg-gradient-to-r from-blue-500 to-blue-700";
}

function proxyModeStatusMeta(proxyMode?: string): StatusMeta {
  const mode = (proxyMode || "none").toLowerCase();
  if (mode === "none" || mode === "direct" || mode === "mock") {
    return { text: "Direct", variant: "secondary" };
  }
  return { text: "Proxy", variant: "success" };
}

function proxyModeGradient(proxyMode?: string): string {
  const mode = (proxyMode || "none").toLowerCase();
  if (mode === "none" || mode === "direct" || mode === "mock") {
    return "bg-gradient-to-r from-slate-500 to-slate-700";
  }
  return "bg-gradient-to-r from-violet-500 to-violet-700";
}

export function AiGatewayView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = useAuthStore((s) => s.token);
  const [copiedEndpoint, setCopiedEndpoint] = useState<string | null>(null);
  const [activeSnippetTab, setActiveSnippetTab] = useState<"openai" | "gemini" | "anthropic" | "cursor">("openai");
  const [origin, setOrigin] = useState<string>("https://pysetu.io");

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.origin) {
      setOrigin(window.location.origin);
    }
  }, []);

  const requestedTab = searchParams.get("tab");
  const initialTab: GatewayTab =
    requestedTab && TAB_IDS.has(requestedTab) ? (requestedTab as GatewayTab) : "connect";
  const [tab, setTab] = useState<GatewayTab>(initialTab);

  const { data, isLoading } = useQuery({
    queryKey: ["gateway-status", token],
    queryFn: () => api.getGatewayStatus(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const status = data ?? EMPTY_GATEWAY_STATUS;

  // Clean endpoints list
  const cleanEndpoints = Array.from(
    new Set(
      status.endpoints
        .map((e) => (e.startsWith("/api/v1") ? e.replace("/api/v1", "/v1") : e))
        .filter((e) => !e.startsWith("/api/v1/"))
    )
  );

  useEffect(() => {
    const next = searchParams.get("tab");
    if (next && TAB_IDS.has(next)) setTab(next as GatewayTab);
  }, [searchParams]);

  function selectTab(next: GatewayTab) {
    setTab(next);
    router.replace(`/ai-gateway?tab=${next}`, { scroll: false });
  }

  async function copyText(text: string, id: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedEndpoint(id);
      window.setTimeout(() => setCopiedEndpoint(null), 2000);
    } catch {
      // clipboard unavailable
    }
  }

  return (
    <div className="space-y-8">
      <QuickLinkPills links={QUICK_LINKS} />

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          variant="hero"
          showTrend={false}
          title="Gateway status"
          value={isLoading ? "..." : status.status.charAt(0).toUpperCase() + status.status.slice(1)}
          change={0}
          icon={Shield}
          iconColor={status.opa_available ? "text-emerald-400" : "text-amber-400"}
          format="raw"
          status={gatewayStatusMeta(status.status, status.opa_available ?? false)}
          valueColor={gatewayStatusGradient(status.status, status.opa_available ?? false)}
        />
        <MetricCard
          variant="hero"
          showTrend={false}
          title="Active upstream"
          value={upstreamLabel(status)}
          change={0}
          icon={Cloud}
          iconColor={
            status.openai_compatible || status.gemini_compatible ? "text-blue-400" : "text-slate-400"
          }
          format="raw"
          status={upstreamStatusMeta(status)}
          valueColor={upstreamGradient(status)}
        />
        <MetricCard
          variant="hero"
          showTrend={false}
          title="Ingress endpoints"
          value={cleanEndpoints.length}
          change={0}
          icon={ArrowRightLeft}
          iconColor="text-violet-400"
          status={{ text: "Available", variant: "success" }}
          valueColor="bg-gradient-to-r from-violet-500 to-violet-700"
        />
        <MetricCard
          variant="hero"
          showTrend={false}
          title="Proxy mode"
          value={!status.proxy_mode || status.proxy_mode === "none" ? "Direct" : status.proxy_mode}
          change={0}
          icon={Route}
          iconColor={status.proxy_mode && status.proxy_mode !== "none" ? "text-amber-400" : "text-slate-400"}
          format="raw"
          status={proxyModeStatusMeta(status.proxy_mode)}
          valueColor={proxyModeGradient(status.proxy_mode)}
        />
      </section>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionTabBar tabs={TABS} active={tab} onChange={selectTab} />
        <Button variant="outline" size="sm" className="gap-1.5" asChild>
          <Link href="/settings/ai-assist#tenant-llm-defaults">
            <Settings2 className="h-3.5 w-3.5" />
            Provider defaults
          </Link>
        </Button>
      </div>

      {tab === "connect" && (
        <div className="space-y-6">
          {/* Base URLs & Ingress Overview */}
          <div className="grid gap-4 lg:grid-cols-12">
            <Card className="border-border/60 bg-card/50 lg:col-span-7">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Shield className="h-4 w-4 text-primary" />
                    Gateway Base URLs & Ingress Endpoints
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => selectTab("edge-mesh")}
                    className="text-xs text-primary hover:text-primary gap-1 h-7 font-medium"
                  >
                    <Globe className="h-3.5 w-3.5" />
                    Manage Edge Nodes
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-2.5">
                  {/* OpenAI Ingress */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-border/60 bg-muted/20">
                    <div>
                      <div className="text-xs font-semibold text-foreground flex items-center gap-2">
                        <span>OpenAI & Standard Base URL</span>
                        <Badge variant="outline" className="text-[10px] py-0 px-1 font-mono text-primary border-primary/30">
                          OPENAI COMPATIBLE
                        </Badge>
                      </div>
                      <code className="text-xs text-primary font-mono block mt-0.5 font-semibold">
                        {origin}/v1
                      </code>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs gap-1 self-start sm:self-center shrink-0"
                      onClick={() => copyText(`${origin}/v1`, "openai-base-url")}
                    >
                      {copiedEndpoint === "openai-base-url" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          Copy Base URL
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Google Gemini Ingress */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-border/60 bg-muted/20">
                    <div>
                      <div className="text-xs font-semibold text-foreground flex items-center gap-2">
                        <span>Google Gemini Native Ingress</span>
                        <Badge variant="outline" className="text-[10px] py-0 px-1 font-mono text-cyan-600 dark:text-cyan-400 border-cyan-500/30">
                          GEMINI v1BETA
                        </Badge>
                      </div>
                      <code className="text-xs text-cyan-600 dark:text-cyan-400 font-mono block mt-0.5 font-semibold">
                        {origin}/v1beta
                      </code>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs gap-1 self-start sm:self-center shrink-0"
                      onClick={() => copyText(`${origin}/v1beta`, "gemini-base-url")}
                    >
                      {copiedEndpoint === "gemini-base-url" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          Copy Gemini URL
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Regional Edge Mesh Ingress */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-primary/20 bg-primary/5">
                    <div>
                      <div className="text-xs font-semibold text-foreground flex items-center gap-2">
                        <Zap className="h-3.5 w-3.5 text-emerald-500" />
                        <span>Regional Edge Mesh (Sub-2ms Latency)</span>
                        <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-[10px] py-0 px-1 font-semibold">
                          LOCAL OPA & DLP
                        </Badge>
                      </div>
                      <code className="text-xs text-foreground font-mono block mt-0.5">
                        https://[region].edge.pysetu.io/v1 <span className="text-muted-foreground">(or internal VPC ingress)</span>
                      </code>
                    </div>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      className="h-7 text-xs gap-1 self-start sm:self-center shrink-0"
                      onClick={() => selectTab("edge-mesh")}
                    >
                      <Server className="h-3.5 w-3.5 text-primary" />
                      View Regional Nodes
                    </Button>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-border/60">
                  <div className="text-xs font-semibold text-foreground mb-2">Supported API Endpoints</div>
                  <ul className="space-y-2 font-mono text-xs">
                    {cleanEndpoints.map((endpoint) => (
                      <li
                        key={endpoint}
                        className="flex items-center justify-between gap-2 rounded-md border border-border/60 bg-muted/20 px-3 py-1.5"
                      >
                        <span>
                          {gatewayHttpMethod(endpoint)} {endpoint}
                        </span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-6 shrink-0 gap-1 font-sans text-[11px] text-muted-foreground"
                          onClick={() => copyText(buildSampleCurl(endpoint, origin), endpoint)}
                          aria-label={`Copy sample cURL for ${endpoint}`}
                        >
                          {copiedEndpoint === endpoint ? (
                            <>
                              <Check className="h-3 w-3 text-emerald-400" />
                              Copied
                            </>
                          ) : (
                            <>
                              <Copy className="h-3 w-3" />
                              cURL
                            </>
                          )}
                        </Button>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge variant="success">OpenAI-compatible</Badge>
                  <Badge variant="secondary">Gemini-compatible</Badge>
                  <Badge variant="outline">Anthropic-compatible</Badge>
                </div>
              </CardContent>
            </Card>

            {/* Quickstart & Pipeline */}
            <Card className="border-border/60 bg-card/50 lg:col-span-5 flex flex-col justify-between">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">SDK & Tool Integration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 flex-1 flex flex-col justify-between">
                {/* Protocol Snippet Switcher */}
                <div>
                  <div className="flex items-center gap-1 border-b border-border/60 pb-1 mb-2">
                    {(["openai", "gemini", "anthropic", "cursor"] as const).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setActiveSnippetTab(mode)}
                        className={`px-2.5 py-1 text-[11px] rounded-md font-medium transition-colors ${
                          activeSnippetTab === mode
                            ? "bg-primary text-primary-foreground shadow-xs font-semibold"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        {mode === "openai" && "OpenAI SDK"}
                        {mode === "gemini" && "Google Gemini"}
                        {mode === "anthropic" && "Anthropic"}
                        {mode === "cursor" && "Cursor / IDE"}
                      </button>
                    ))}
                  </div>

                  <div className="relative">
                    <pre className="p-3 rounded-lg bg-muted font-mono text-[11px] text-foreground overflow-x-auto leading-relaxed border border-border/80 max-h-48">
                      {activeSnippetTab === "openai" &&
`from openai import OpenAI

client = OpenAI(
    base_url="${origin}/v1",
    api_key="pysetu_live_secret_..."
)

response = client.chat.completions.create(
    model="gpt-4o", # or claude-3-7-sonnet
    messages=[{"role": "user", "content": "Hello!"}]
)`}

                      {activeSnippetTab === "gemini" &&
`import google.generativeai as genai

# Configure Google GenAI SDK to route via PySetu
genai.configure(
    api_key="pysetu_live_secret_...",
    client_options={"api_endpoint": "${origin}"}
)

model = genai.GenerativeModel("gemini-1.5-pro")
response = model.generate_content("Hello from PySetu!")`}

                      {activeSnippetTab === "anthropic" &&
`from anthropic import Anthropic

client = Anthropic(
    base_url="${origin}",
    api_key="pysetu_live_secret_..."
)

response = client.messages.create(
    model="claude-3-7-sonnet",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
)`}

                      {activeSnippetTab === "cursor" &&
`# Cursor / VS Code / Claude Code Settings:
OpenAI Base URL: ${origin}/v1
API Key: pysetu_live_secret_...
Model Override: gpt-4o or claude-3-7-sonnet`}
                    </pre>

                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        const snippet =
                          activeSnippetTab === "openai"
                            ? `from openai import OpenAI\n\nclient = OpenAI(base_url="${origin}/v1", api_key="pysetu_live_secret_...")\nresponse = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": "Hello!"}])`
                            : activeSnippetTab === "gemini"
                            ? `import google.generativeai as genai\n\ngenai.configure(api_key="pysetu_live_secret_...", client_options={"api_endpoint": "${origin}"})\nmodel = genai.GenerativeModel("gemini-1.5-pro")\nresponse = model.generate_content("Hello from PySetu!")`
                            : activeSnippetTab === "anthropic"
                            ? `from anthropic import Anthropic\n\nclient = Anthropic(base_url="${origin}", api_key="pysetu_live_secret_...")`
                            : `OpenAI Base URL: ${origin}/v1\nAPI Key: pysetu_live_secret_...`;
                        copyText(snippet, "active-snippet");
                      }}
                      className="absolute top-2 right-2 h-6 text-[10px] gap-1"
                    >
                      {copiedEndpoint === "active-snippet" ? (
                        <Check className="h-3 w-3 text-emerald-400" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                      {copiedEndpoint === "active-snippet" ? "Copied" : "Copy"}
                    </Button>
                  </div>
                </div>

                <div className="pt-2 border-t border-border/60">
                  <div className="text-[11px] font-semibold text-foreground mb-1.5">Inspection Pipeline</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-[11px] text-muted-foreground">
                    {PIPELINE_STEPS.map((step) => (
                      <div key={step} className="flex items-center gap-1.5">
                        <CheckCircle2 className="h-3 w-3 shrink-0 text-emerald-400" />
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {tab === "edge-mesh" && <TenantEdgeMeshPanel />}

      {tab === "test" && <GatewayTester />}

      {tab === "rag" && <RagGatewayTester />}

      {tab === "compatibility" && <CompatibilityCenterView embedded />}
    </div>
  );
}
